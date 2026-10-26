#!/usr/bin/env python3
"""Build reproducible B43 feature snapshots from historical B39/B40/B42 stores.

The collector is deliberately strict: it skips model/task combinations without
sufficient observed attempts, a complete priced-usage history, or an exact B42
quality profile. It does not fabricate neutral values for missing evidence.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.models.contracts import ModelTask
from core.models.quality import JsonFileQualityProfileStore
from core.models.usage import JsonFileModelUsageStore, ModelUsageRecord


def _load_health_states(path: Path | None) -> tuple[dict[str, dict[str, Any]], list[str]]:
    if path is None:
        return {}, []
    if not path.is_file():
        raise ValueError(f"health store does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid health store JSON in {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("health store must be a JSON object keyed by provider name")
    states: dict[str, dict[str, Any]] = {}
    for provider, raw in payload.items():
        if not isinstance(raw, dict):
            raise ValueError(f"health state for {provider!r} must be a JSON object")
        states[str(provider)] = raw
    return states, []


def _usage_groups(records: tuple[ModelUsageRecord, ...]) -> dict[tuple[str, str, ModelTask], list[ModelUsageRecord]]:
    groups: dict[tuple[str, str, ModelTask], list[ModelUsageRecord]] = {}
    for record in records:
        requested_model = record.metadata.get("requested_model")
        model_key = (
            requested_model.strip()
            if isinstance(requested_model, str) and requested_model.strip()
            else record.model
        )
        if not record.provider or not model_key:
            continue
        groups.setdefault((record.provider, model_key, record.task), []).append(record)
    return groups


def _exact_quality_profile(
    profiles: tuple[Any, ...],
    provider: str,
    model: str,
    task: ModelTask,
) -> Any | None:
    exact = [
        item for item in profiles
        if item.provider == provider and item.model == model and item.task == task
    ]
    if not exact:
        return None
    # An exact route/model identity can have separate records for family metadata.
    return max(exact, key=lambda item: (item.sample_size, item.last_observed_at))


def build_snapshot(
    *,
    usage_store_path: Path,
    quality_store_path: Path,
    health_store_path: Path | None,
    latency_scale_ms: float = 1000.0,
    cost_scale_usd: float = 0.01,
    prior_quality: float = 0.5,
    min_attempts: int = 3,
    min_quality_samples: int = 1,
) -> dict[str, Any]:
    if latency_scale_ms <= 0 or not math.isfinite(latency_scale_ms):
        raise ValueError("latency-scale-ms must be a finite number > 0")
    if cost_scale_usd <= 0 or not math.isfinite(cost_scale_usd):
        raise ValueError("cost-scale-usd must be a finite number > 0")
    if not 0 <= prior_quality <= 1:
        raise ValueError("prior-quality must be between 0 and 1")
    if min_attempts < 1 or min_quality_samples < 1:
        raise ValueError("minimum evidence counts must be >= 1")
    if not usage_store_path.is_file():
        raise ValueError(f"usage store does not exist: {usage_store_path}")
    if not quality_store_path.is_file():
        raise ValueError(f"quality profile store does not exist: {quality_store_path}")

    usage_records = JsonFileModelUsageStore(usage_store_path).records()
    quality_profiles = JsonFileQualityProfileStore(quality_store_path).all()
    health_states, _ = _load_health_states(health_store_path)

    grouped = _usage_groups(usage_records)
    features: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    health_filtered = 0

    for (provider, model, task), records in sorted(
        grouped.items(), key=lambda item: (item[0][2].value, item[0][0], item[0][1])
    ):
        state = health_states.get(provider)
        if state is not None:
            if state.get("enabled") is False:
                skipped.append({"provider": provider, "model": model, "task": task.value, "reason": "provider_disabled_in_b39_health_store"})
                health_filtered += 1
                continue
            if state.get("circuit_open") is True:
                skipped.append({"provider": provider, "model": model, "task": task.value, "reason": "provider_circuit_open_in_b39_health_store"})
                health_filtered += 1
                continue

        if len(records) < min_attempts:
            skipped.append({"provider": provider, "model": model, "task": task.value, "reason": f"insufficient_attempts:{len(records)}<{min_attempts}"})
            continue

        successful = sum(1 for item in records if item.success)
        reliability = successful / len(records)
        mean_latency = sum(item.latency_ms for item in records) / len(records)
        if not math.isfinite(mean_latency) or mean_latency < 0:
            skipped.append({"provider": provider, "model": model, "task": task.value, "reason": "invalid_latency_telemetry"})
            continue
        latency_score = 1.0 / (1.0 + mean_latency / latency_scale_ms)

        successful_records = [item for item in records if item.success]
        priced_records = [
            item for item in successful_records
            if item.estimated_cost_usd is not None
        ]
        if not successful_records or len(priced_records) != len(successful_records):
            skipped.append({
                "provider": provider,
                "model": model,
                "task": task.value,
                "reason": (
                    f"incomplete_pricing:{len(priced_records)}/"
                    f"{len(successful_records)}_successful_attempts_priced"
                ),
            })
            continue
        mean_cost = sum(float(item.estimated_cost_usd) for item in priced_records) / len(priced_records)
        if not math.isfinite(mean_cost) or mean_cost < 0:
            skipped.append({"provider": provider, "model": model, "task": task.value, "reason": "invalid_priced_usage_telemetry"})
            continue
        cost_score = 1.0 / (1.0 + mean_cost / cost_scale_usd)

        profile = _exact_quality_profile(quality_profiles, provider, model, task)
        if profile is None:
            skipped.append({"provider": provider, "model": model, "task": task.value, "reason": "missing_exact_b42_quality_profile"})
            continue
        if profile.sample_size < min_quality_samples:
            skipped.append({"provider": provider, "model": model, "task": task.value, "reason": f"insufficient_quality_samples:{profile.sample_size}<{min_quality_samples}"})
            continue
        quality_score = prior_quality + profile.confidence * (profile.score - prior_quality)
        quality_score = max(0.0, min(1.0, quality_score))

        features.append({
            "provider": provider,
            "model": model,
            "task": task.value,
            "reliability": reliability,
            "latency": latency_score,
            "quality": quality_score,
            "cost": cost_score,
            "priority": 0,
            "quality_last_observed_at": profile.last_observed_at.isoformat(),
            "evidence": {
                "usage_attempts": len(records),
                "successful_attempts": successful,
                "observed_response_models": sorted({item.model for item in records}),
                "mean_latency_ms": mean_latency,
                "priced_attempts": len(priced_records),
                "mean_estimated_cost_usd": mean_cost,
                "quality_samples": profile.sample_size,
                "quality_confidence": profile.confidence,
                "quality_last_observed_at": profile.last_observed_at.isoformat(),
            },
        })

    generated_at = datetime.now(timezone.utc).isoformat()
    if not features:
        # Emit diagnostics while ensuring the current proposal CLI does not
        # accidentally treat a missing evidence set as a neutral feature vector.
        return {
            "schema_version": 1,
            "generated_at": generated_at,
            "source": "historical_b39_optional_b40_b42_store_snapshot",
            "features": [],
            "included_model_tasks": 0,
            "skipped_model_tasks": len(skipped),
            "skipped": skipped,
            "health_filtered_model_tasks": health_filtered,
            "scales": {
                "latency_scale_ms": latency_scale_ms,
                "cost_scale_usd": cost_scale_usd,
                "prior_quality": prior_quality,
            },
        }

    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "source": "historical_b39_optional_b40_b42_store_snapshot",
        "features": features,
        "included_model_tasks": len(features),
        "skipped_model_tasks": len(skipped),
        "skipped": skipped,
        "health_filtered_model_tasks": health_filtered,
        "scales": {
            "latency_scale_ms": latency_scale_ms,
            "cost_scale_usd": cost_scale_usd,
            "prior_quality": prior_quality,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build B43 normalized features from observed B40 usage and exact B42 quality profiles."
    )
    parser.add_argument("--usage-store", type=Path, default=Path("./data/model-usage.json"))
    parser.add_argument("--quality-store", type=Path, default=Path("./data/model-quality.json"))
    parser.add_argument("--health-store", type=Path, default=None, help="Optional B39 provider health JSON store")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--latency-scale-ms", type=float, default=1000.0)
    parser.add_argument("--cost-scale-usd", type=float, default=0.01)
    parser.add_argument("--prior-quality", type=float, default=0.5)
    parser.add_argument("--min-attempts", type=int, default=3)
    parser.add_argument("--min-quality-samples", type=int, default=1)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        inputs = [args.usage_store.resolve(), args.quality_store.resolve()]
        if args.health_store is not None:
            inputs.append(args.health_store.resolve())
        if args.output.resolve() in set(inputs):
            raise ValueError("output path must not overwrite an input telemetry store")

        snapshot = build_snapshot(
            usage_store_path=args.usage_store,
            quality_store_path=args.quality_store,
            health_store_path=args.health_store,
            latency_scale_ms=args.latency_scale_ms,
            cost_scale_usd=args.cost_scale_usd,
            prior_quality=args.prior_quality,
            min_attempts=args.min_attempts,
            min_quality_samples=args.min_quality_samples,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({
            "output_path": str(args.output),
            "included_model_tasks": snapshot["included_model_tasks"],
            "skipped_model_tasks": snapshot["skipped_model_tasks"],
            "health_filtered_model_tasks": snapshot["health_filtered_model_tasks"],
            "result_file_written": True,
        }, ensure_ascii=False, indent=2))
        return 0 if snapshot["features"] else 2
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
