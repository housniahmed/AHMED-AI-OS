"""Versioned JSON serialization for B32 evaluation runs.

This is an interchange format for offline evaluation and policy-learning workflows.
It deliberately does not serialize arbitrary Python objects: evaluation outputs
must be JSON-compatible if a run is exported.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from core.evaluation.models import (
    EvaluationResult,
    EvaluationRun,
    EvaluationStatus,
    MetricResult,
)

SCHEMA_VERSION = 1


def evaluation_run_to_dict(run: EvaluationRun) -> dict[str, Any]:
    """Convert an evaluation run to the stable, versioned interchange schema."""
    return {
        "schema_version": SCHEMA_VERSION,
        "id": str(run.id),
        "started_at": run.started_at.isoformat(),
        "results": [
            {
                "case_id": str(result.case_id),
                "status": result.status.value,
                "metrics": [
                    {
                        "name": metric.name,
                        "score": metric.score,
                        "passed": metric.passed,
                        "threshold": metric.threshold,
                        "details": metric.details,
                    }
                    for metric in result.metrics
                ],
                "output": result.output,
                "error": result.error,
                "duration_ms": result.duration_ms,
                "metadata": result.metadata,
            }
            for result in run.results
        ],
    }


def evaluation_run_from_dict(payload: dict[str, Any]) -> EvaluationRun:
    """Parse a versioned evaluation-run document with strict structural checks."""
    if not isinstance(payload, dict):
        raise ValueError("evaluation run document must be a JSON object")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported evaluation run schema_version: {payload.get('schema_version')!r}")
    if not isinstance(payload.get("results"), list):
        raise ValueError("evaluation run 'results' must be a JSON array")

    try:
        run_id = UUID(str(payload["id"]))
        started_at = _parse_datetime(payload["started_at"], "started_at")
        results = tuple(_result_from_dict(item) for item in payload["results"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid evaluation run document: {exc}") from exc
    return EvaluationRun(id=run_id, started_at=started_at, results=results)


def _result_from_dict(raw: Any) -> EvaluationResult:
    if not isinstance(raw, dict):
        raise ValueError("each evaluation result must be a JSON object")
    metrics_raw = raw.get("metrics", [])
    if not isinstance(metrics_raw, list):
        raise ValueError("result 'metrics' must be a JSON array")
    metadata = raw.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("result 'metadata' must be a JSON object")

    metrics: list[MetricResult] = []
    for item in metrics_raw:
        if not isinstance(item, dict):
            raise ValueError("each metric must be a JSON object")
        details = item.get("details", {})
        if not isinstance(details, dict):
            raise ValueError("metric 'details' must be a JSON object")
        metrics.append(
            MetricResult(
                name=str(item["name"]),
                score=float(item["score"]),
                passed=_as_bool(item["passed"], "metric passed"),
                threshold=float(item["threshold"]) if item.get("threshold") is not None else None,
                details=details,
            )
        )

    duration = raw.get("duration_ms")
    return EvaluationResult(
        case_id=UUID(str(raw["case_id"])),
        status=EvaluationStatus(str(raw["status"])),
        metrics=tuple(metrics),
        output=raw.get("output"),
        error=str(raw["error"]) if raw.get("error") is not None else None,
        duration_ms=float(duration) if duration is not None else None,
        metadata=metadata,
    )


def _as_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a JSON boolean")
    return value


def _parse_datetime(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be an ISO-8601 string")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def save_evaluation_run(run: EvaluationRun, path: str | Path) -> None:
    """Persist a run as JSON; raises if outputs/metadata are not JSON-compatible."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(
        evaluation_run_to_dict(run),
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    )
    destination.write_text(serialized + "\n", encoding="utf-8")


def load_evaluation_run(path: str | Path) -> EvaluationRun:
    """Load a JSON evaluation run using the versioned interchange schema."""
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid evaluation run JSON in {source}") from exc
    return evaluation_run_from_dict(payload)
