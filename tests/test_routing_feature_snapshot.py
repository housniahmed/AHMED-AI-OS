import json
from datetime import datetime, timezone
from pathlib import Path

from core.models.contracts import ModelTask
from core.models.quality import JsonFileQualityProfileStore, QualityProfile
from core.models.usage import JsonFileModelUsageStore, ModelUsageRecord
from scripts.build_routing_feature_snapshot import build_snapshot


def _write_usage(
    path: Path,
    *,
    provider: str,
    model: str,
    priced: bool = True,
    reported_model: str | None = None,
) -> None:
    store = JsonFileModelUsageStore(path)
    for index, success in enumerate((True, True, False)):
        store.record(
            ModelUsageRecord(
                task=ModelTask.REASONING,
                provider=provider,
                model=reported_model or model,
                latency_ms=(100.0 + index * 100.0),
                success=success,
                estimated_cost_usd=(0.001 if priced and success else None),
                metadata={"requested_model": model},
            )
        )


def _profile(
    store: JsonFileQualityProfileStore,
    *,
    provider: str,
    model: str,
    score: float,
    confidence: float,
) -> None:
    store.save(
        QualityProfile(
            provider=provider,
            model=model,
            task=ModelTask.REASONING,
            model_family="test-family",
            score=score,
            confidence=confidence,
            sample_size=5,
            pass_rate=0.8,
            passed_evaluations=4,
            failed_evaluations=1,
            trend=0.0,
            last_observed_score=score,
            last_observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    )


def test_snapshot_uses_observed_usage_and_confidence_blended_exact_quality(tmp_path):
    usage_path = tmp_path / "usage.json"
    quality_path = tmp_path / "quality.json"
    health_path = tmp_path / "health.json"

    _write_usage(
        usage_path,
        provider="provider-a",
        model="model-a",
        reported_model="model-a-serving-v2",
    )
    _write_usage(usage_path, provider="provider-b", model="model-b")
    quality_store = JsonFileQualityProfileStore(quality_path)
    _profile(quality_store, provider="provider-a", model="model-a", score=0.9, confidence=0.8)
    _profile(quality_store, provider="provider-b", model="model-b", score=0.7, confidence=0.5)
    health_path.write_text(
        json.dumps({
            "provider-a": {"enabled": True, "circuit_open": False},
            "provider-b": {"enabled": True, "circuit_open": False},
        }),
        encoding="utf-8",
    )

    snapshot = build_snapshot(
        usage_store_path=usage_path,
        quality_store_path=quality_path,
        health_store_path=health_path,
        latency_scale_ms=1000,
        cost_scale_usd=0.01,
        prior_quality=0.5,
        min_attempts=3,
    )

    assert snapshot["included_model_tasks"] == 2
    assert snapshot["skipped_model_tasks"] == 0
    first = next(item for item in snapshot["features"] if item["model"] == "model-a")
    assert first["reliability"] == 2 / 3
    assert first["latency"] < 1
    assert first["cost"] == 1 / (1 + 0.001 / 0.01)
    assert first["quality"] == 0.5 + 0.8 * (0.9 - 0.5)
    assert first["quality_last_observed_at"] == "2026-01-01T00:00:00+00:00"
    assert first["evidence"]["usage_attempts"] == 3
    assert first["evidence"]["priced_attempts"] == 2
    assert first["evidence"]["observed_response_models"] == ["model-a-serving-v2"]


def test_snapshot_skips_incomplete_pricing_missing_quality_and_open_circuit(tmp_path):
    usage_path = tmp_path / "usage.json"
    quality_path = tmp_path / "quality.json"
    health_path = tmp_path / "health.json"

    _write_usage(usage_path, provider="provider-a", model="unpriced-model", priced=False)
    _write_usage(usage_path, provider="provider-b", model="open-model", priced=True)
    quality_store = JsonFileQualityProfileStore(quality_path)
    _profile(quality_store, provider="provider-a", model="unpriced-model", score=0.9, confidence=0.8)
    _profile(quality_store, provider="provider-b", model="open-model", score=0.7, confidence=0.5)
    health_path.write_text(
        json.dumps({
            "provider-a": {"enabled": True, "circuit_open": False},
            "provider-b": {"enabled": True, "circuit_open": True},
        }),
        encoding="utf-8",
    )

    snapshot = build_snapshot(
        usage_store_path=usage_path,
        quality_store_path=quality_path,
        health_store_path=health_path,
        min_attempts=3,
    )

    assert snapshot["features"] == []
    reasons = {item["model"]: item["reason"] for item in snapshot["skipped"]}
    assert reasons["unpriced-model"].startswith("incomplete_pricing")
    assert reasons["open-model"] == "provider_circuit_open_in_b39_health_store"
