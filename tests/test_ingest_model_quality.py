import json
from datetime import datetime, timezone
from uuid import UUID

from core.evaluation.models import EvaluationResult, EvaluationRun, EvaluationStatus, MetricResult
from core.evaluation.serialization import save_evaluation_run
from core.models.contracts import ModelTask
from core.models.quality import JsonFileQualityProfileStore
from scripts.ingest_model_quality import main


def test_ingests_attributed_historical_b32_scores_into_exact_b42_profiles(tmp_path, capsys):
    run_path = tmp_path / "historical-run.json"
    profile_path = tmp_path / "quality.json"
    run = EvaluationRun(
        started_at=datetime(2025, 12, 1, tzinfo=timezone.utc),
        results=(
            EvaluationResult(
                case_id=UUID(int=1),
                status=EvaluationStatus.PASSED,
                metrics=(MetricResult("correctness", 0.9, True),),
                metadata={
                    "provider": "provider-a",
                    "model": "model-a",
                    "task": ModelTask.REASONING.value,
                    "model_family": "test-family",
                },
            ),
            EvaluationResult(
                case_id=UUID(int=2),
                status=EvaluationStatus.FAILED,
                metrics=(MetricResult("correctness", 0.4, False),),
                metadata={
                    "provider": "provider-b",
                    "model": "model-b",
                    "task": ModelTask.REASONING.value,
                    "model_family": "test-family",
                },
            ),
            EvaluationResult(
                case_id=UUID(int=3),
                status=EvaluationStatus.PASSED,
                metrics=(MetricResult("correctness", 1.0, True),),
                metadata={"task": ModelTask.REASONING.value},
            ),
        ),
    )
    save_evaluation_run(run, run_path)

    exit_code = main(
        [
            "--evaluation-run",
            str(run_path),
            "--quality-store",
            str(profile_path),
        ]
    )

    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["input_result_count"] == 3
    assert report["ingested_observation_count"] == 2
    assert report["skipped_result_count"] == 1
    store = JsonFileQualityProfileStore(profile_path)
    exact_profiles = [
        item for item in store.all()
        if item.provider in {"provider-a", "provider-b"} and item.model in {"model-a", "model-b"}
    ]
    assert len(exact_profiles) == 2
    assert {item.sample_size for item in exact_profiles} == {1}
    assert all(item.last_observed_at > run.started_at for item in exact_profiles)
