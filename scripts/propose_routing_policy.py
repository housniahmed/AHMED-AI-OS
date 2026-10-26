#!/usr/bin/env python3
"""Create B43 routing-policy proposals from a real B32 evaluation run.

This command is intentionally proposal-only: it never calls optimizer.approve()
and never activates a candidate policy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from core.evaluation.serialization import load_evaluation_run
from core.models.contracts import ModelTask
from core.models.policy_learning import (
    JsonFilePolicyLifecycleStore,
    PolicyDatasetBuilder,
    PolicyFeatureVector,
    PolicyOptimizationConfig,
    RoutingPolicyOptimizer,
)


def _parse_aware_timestamp(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"feature snapshot '{field_name}' must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"feature snapshot '{field_name}' must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"feature snapshot '{field_name}' must include a timezone")
    return parsed


def _load_feature_snapshot(
    path: Path,
    *,
    evaluation_started_at: datetime,
) -> dict[tuple[str, str, ModelTask], PolicyFeatureVector]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid feature snapshot JSON in {path}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("feature snapshot must be a JSON object with schema_version=1")
    if evaluation_started_at.tzinfo is None or evaluation_started_at.utcoffset() is None:
        raise ValueError("evaluation run started_at must include a timezone")
    snapshot_generated_at = _parse_aware_timestamp(payload.get("generated_at"), "generated_at")
    if snapshot_generated_at >= evaluation_started_at:
        raise ValueError(
            "feature snapshot must be generated before the evaluation run starts; "
            "use historical telemetry to avoid evaluation leakage"
        )
    records = payload.get("features")
    if not isinstance(records, list):
        raise ValueError("feature snapshot 'features' must be a JSON array")

    snapshot: dict[tuple[str, str, ModelTask], PolicyFeatureVector] = {}
    for index, item in enumerate(records):
        if not isinstance(item, dict):
            raise ValueError(f"feature entry {index} must be a JSON object")
        provider = str(item.get("provider", "")).strip()
        model = str(item.get("model", "")).strip()
        try:
            task = ModelTask(str(item.get("task", "")))
        except ValueError as exc:
            raise ValueError(f"feature entry {index} has an unsupported task") from exc
        if not provider or not model:
            raise ValueError(f"feature entry {index} requires provider and model")
        key = (provider, model, task)
        if key in snapshot:
            raise ValueError(f"duplicate feature snapshot entry for {provider}/{model}/{task.value}")
        quality_observed_at = _parse_aware_timestamp(
            item.get("quality_last_observed_at"),
            f"features[{index}].quality_last_observed_at",
        )
        if quality_observed_at > snapshot_generated_at:
            raise ValueError(
                f"feature entry {index}: quality profile timestamp is newer than the feature snapshot"
            )
        if quality_observed_at >= evaluation_started_at:
            raise ValueError(
                f"feature entry {index}: B42 quality evidence must predate the evaluation run"
            )

        values: dict[str, float] = {}
        for name in ("reliability", "latency", "quality", "cost"):
            value = item.get(name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"feature entry {index}: '{name}' must be a number in [0, 1]")
            values[name] = float(value)
        priority = item.get("priority", 0)
        if isinstance(priority, bool) or not isinstance(priority, int):
            raise ValueError(f"feature entry {index}: 'priority' must be an integer")
        snapshot[key] = PolicyFeatureVector(**values, priority=priority)
    if not snapshot:
        raise ValueError("feature snapshot contains no model feature records")
    return snapshot


def _json_safe_proposal(proposal: Any, active_policy_unchanged: bool) -> dict[str, Any]:
    stats = proposal.stats
    return {
        "proposal_id": str(proposal.id),
        "task": proposal.task.value,
        "status": proposal.status.value,
        "reason": proposal.reason,
        "baseline_revision": proposal.baseline_revision,
        "training_samples": stats.training_samples,
        "validation_samples": stats.validation_samples,
        "baseline_validation_score": stats.baseline_validation_score,
        "candidate_validation_score": stats.candidate_validation_score,
        "mean_uplift": stats.mean_uplift,
        "standard_error": stats.standard_error,
        "confidence_lower_bound": stats.confidence_lower_bound,
        "gate_eligible": stats.gate_eligible,
        "active_policy_unchanged": active_policy_unchanged,
        "candidate_weights": {
            "reliability": proposal.candidate_policy.reliability_weight,
            "latency": proposal.candidate_policy.latency_weight,
            "quality": proposal.candidate_policy.quality_weight,
            "cost": proposal.candidate_policy.cost_weight,
        },
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create non-activating B43 routing-policy proposals from a B32 evaluation run."
    )
    parser.add_argument("--evaluation-run", required=True, type=Path, help="JSON exported with core.evaluation.serialization.save_evaluation_run")
    parser.add_argument("--features", required=True, type=Path, help="Version 1 normalized B39/B40/B42 feature snapshot JSON")
    parser.add_argument(
        "--store-path",
        type=Path,
        default=Path(os.getenv("MODEL_ROUTING_POLICY_STORE_PATH", "./data/model-routing-policies.json")),
        help="Persistent B43 proposal/audit store (default: MODEL_ROUTING_POLICY_STORE_PATH or ./data/model-routing-policies.json)",
    )
    parser.add_argument("--dataset-id", help="Optional label; otherwise a hash of both input files is used")
    parser.add_argument("--min-training-samples", type=int, default=20)
    parser.add_argument("--min-validation-samples", type=int, default=20)
    parser.add_argument("--min-mean-uplift", type=float, default=0.02)
    parser.add_argument("--confidence-z", type=float, default=1.96)
    parser.add_argument("--exploration-rate", type=float, default=0.35)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if not args.evaluation_run.is_file():
            raise ValueError(f"evaluation run file does not exist: {args.evaluation_run}")
        if not args.features.is_file():
            raise ValueError(f"feature snapshot file does not exist: {args.features}")
        if args.store_path.resolve() in {args.evaluation_run.resolve(), args.features.resolve()}:
            raise ValueError("policy store path must not overwrite either input file")

        run = load_evaluation_run(args.evaluation_run)
        feature_snapshot = _load_feature_snapshot(
            args.features, evaluation_started_at=run.started_at
        )
        config = PolicyOptimizationConfig(
            min_training_samples=args.min_training_samples,
            min_validation_samples=args.min_validation_samples,
            min_mean_uplift=args.min_mean_uplift,
            confidence_z=args.confidence_z,
            exploration_rate=args.exploration_rate,
        )
        dataset_id = args.dataset_id or (
            f"sha256:{_sha256(args.evaluation_run)[:16]}:{_sha256(args.features)[:16]}"
        )
        report = PolicyDatasetBuilder.from_evaluation_run(
            run,
            feature_resolver=lambda provider, model, task: feature_snapshot.get(
                (provider, model, task)
            ),
        )

        store = JsonFilePolicyLifecycleStore(args.store_path)
        optimizer = RoutingPolicyOptimizer(store=store, config=config)
        tasks = sorted({sample.task for sample in report.samples}, key=lambda task: task.value)
        proposals: list[dict[str, Any]] = []
        for task in tasks:
            task_samples = tuple(sample for sample in report.samples if sample.task == task)
            proposal = optimizer.propose(task, task_samples, dataset_id=dataset_id)
            active_policy = optimizer.get_active_policy(task)
            proposals.append(
                _json_safe_proposal(
                    proposal,
                    active_policy_unchanged=(active_policy == proposal.baseline_policy),
                )
            )

        result = {
            "schema_version": 1,
            "evaluation_run_id": str(run.id),
            "dataset_id": dataset_id,
            "paired_sample_count": len(report.samples),
            "paired_samples_by_task": {
                task.value: sum(sample.task == task for sample in report.samples)
                for task in tasks
            },
            "skipped_result_count": report.skipped_results,
            "skipped_group_count": report.skipped_groups,
            "skip_reasons": list(report.reasons),
            "proposal_count": len(proposals),
            "proposals": proposals,
            "store_path": str(args.store_path),
            "activation_performed": False,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0 if proposals else 2
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
