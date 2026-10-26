import json
from pathlib import Path
from uuid import UUID

from core.evaluation.models import (
    EvaluationResult,
    EvaluationRun,
    EvaluationStatus,
    MetricResult,
)
from core.evaluation.serialization import (
    evaluation_run_from_dict,
    evaluation_run_to_dict,
    save_evaluation_run,
)
from core.models.contracts import ModelTask
from core.models.policy_learning import JsonFilePolicyLifecycleStore
from scripts.propose_routing_policy import main


def _benchmark_run(count: int = 48) -> EvaluationRun:
    results = []
    for index in range(count):
        group = f"case-{index:03d}"
        results.extend(
            (
                EvaluationResult(
                    case_id=UUID(int=(index * 2) + 1),
                    status=EvaluationStatus.PASSED,
                    metrics=(MetricResult("quality", 0.60, True),),
                    output={"fixture": "test-only", "model": "cheap-model"},
                    metadata={
                        "provider": "test-provider",
                        "model": "cheap-model",
                        "task": "reasoning",
                        "benchmark_case_id": group,
                    },
                ),
                EvaluationResult(
                    case_id=UUID(int=(index * 2) + 2),
                    status=EvaluationStatus.PASSED,
                    metrics=(MetricResult("quality", 0.96, True),),
                    output={"fixture": "test-only", "model": "quality-model"},
                    metadata={
                        "provider": "test-provider",
                        "model": "quality-model",
                        "task": "reasoning",
                        "benchmark_case_id": group,
                    },
                ),
            )
        )
    return EvaluationRun(results=tuple(results))


def _features(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": "2026-01-01T00:00:00+00:00",
                "features": [
                    {
                        "provider": "test-provider",
                        "model": "cheap-model",
                        "task": "reasoning",
                        "quality_last_observed_at": "2025-12-15T00:00:00+00:00",
                        "reliability": 0.95,
                        "latency": 0.70,
                        "quality": 0.60,
                        "cost": 1.00,
                    },
                    {
                        "provider": "test-provider",
                        "model": "quality-model",
                        "task": "reasoning",
                        "quality_last_observed_at": "2025-12-15T00:00:00+00:00",
                        "reliability": 0.90,
                        "latency": 0.55,
                        "quality": 0.95,
                        "cost": 0.25,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def test_evaluation_run_serialization_round_trip():
    run = _benchmark_run(count=1)
    restored = evaluation_run_from_dict(evaluation_run_to_dict(run))
    assert restored.id == run.id
    assert restored.started_at == run.started_at
    assert restored.results == run.results


def test_cli_creates_proposal_without_activating_candidate(tmp_path, capsys):
    run_path = tmp_path / "evaluation-run.json"
    feature_path = tmp_path / "features.json"
    store_path = tmp_path / "policies.json"
    save_evaluation_run(_benchmark_run(), run_path)
    _features(feature_path)

    exit_code = main(
        [
            "--evaluation-run",
            str(run_path),
            "--features",
            str(feature_path),
            "--store-path",
            str(store_path),
            "--min-training-samples",
            "4",
            "--min-validation-samples",
            "4",
            "--min-mean-uplift",
            "0.01",
            "--exploration-rate",
            "1.0",
        ]
    )
    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["paired_sample_count"] == 48
    assert report["proposal_count"] == 1
    assert report["activation_performed"] is False
    proposal_report = report["proposals"][0]
    assert proposal_report["active_policy_unchanged"] is True

    store = JsonFilePolicyLifecycleStore(store_path)
    proposal_id = UUID(proposal_report["proposal_id"])
    proposal = store.get_proposal(proposal_id)
    active = store.active_revision(ModelTask.REASONING)
    assert proposal is not None
    assert active is not None
    assert active.policy == proposal.baseline_policy
    assert proposal.status.value != "active"
    assert not any(event.action == "policy_activated" for event in store.audit_events())


def test_cli_does_not_create_proposal_when_no_paired_features_exist(tmp_path, capsys):
    run_path = tmp_path / "evaluation-run.json"
    feature_path = tmp_path / "features.json"
    store_path = tmp_path / "policies.json"
    save_evaluation_run(_benchmark_run(count=2), run_path)
    feature_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "features": [
                    {
                        "provider": "test-provider",
                        "model": "cheap-model",
                        "task": "reasoning",
                        "reliability": 0.95,
                        "latency": 0.70,
                        "quality": 0.60,
                        "cost": 1.00,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--evaluation-run",
            str(run_path),
            "--features",
            str(feature_path),
            "--store-path",
            str(store_path),
        ]
    )
    assert exit_code == 2
    report = json.loads(capsys.readouterr().out)
    assert report["paired_sample_count"] == 0
    assert report["proposal_count"] == 0
    assert report["activation_performed"] is False
    assert not store_path.exists()
