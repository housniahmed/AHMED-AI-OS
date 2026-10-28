from pathlib import Path

from core.evaluation.models import EvaluationCase
from core.models.contracts import ModelTask
from core.models.providers import StaticModelProvider
from core.models.router import ModelRoute, ModelRouter
from scripts.run_model_routing_benchmark import (
    DeterministicBenchmarkMetric,
    _build_evaluation_run,
    _load_dataset,
)


def test_benchmark_runner_evaluates_every_candidate_on_same_case():
    router = ModelRouter(
        providers={
            "provider-a": StaticModelProvider("provider-a", "The answer is a blue square."),
            "provider-b": StaticModelProvider("provider-b", "The answer is a blue circle."),
        },
        routes=(
            ModelRoute(ModelTask.REASONING, "provider-a", "model-a"),
            ModelRoute(ModelTask.REASONING, "provider-b", "model-b"),
        ),
    )
    dataset = [
        {
            "id": "reasoning-001",
            "name": "shape attributes",
            "input": "Name the color and shape of the object.",
            "task": ModelTask.REASONING,
            "expected": {"kind": "required_terms", "terms": ["blue", "square"]},
            "threshold": 0.75,
        },
        {
            "id": "reasoning-002",
            "name": "repeat the shape attributes",
            "input": "Repeat the color and shape.",
            "task": ModelTask.REASONING,
            "expected": {"kind": "required_terms", "terms": ["blue", "square"]},
            "threshold": 0.75,
        },
    ]

    run, report = _build_evaluation_run(
        router,
        dataset,
        limit_per_task=10,
        max_tokens=64,
        temperature=0.0,
    )

    assert len(run.results) == 4
    assert all(item.duration_ms is not None and item.duration_ms >= 0 for item in run.results)
    assert report["logical_evaluation_calls"] == 4
    assert report["by_task"]["reasoning"]["benchmark_cases"] == 2
    # The benchmark uses isolated in-memory health and usage stores.
    assert router.usage_store.records() == ()
    assert router.provider_status()["provider-a"].successes == 0
    assert router.provider_status()["provider-b"].successes == 0
    for case_id in ("reasoning-001", "reasoning-002"):
        paired = [item for item in run.results if item.metadata["benchmark_case_id"] == case_id]
        assert {item.metadata["provider"] for item in paired} == {"provider-a", "provider-b"}
        assert {item.metadata["model"] for item in paired} == {"model-a", "model-b"}
    results_by_provider = {
        item.metadata["provider"]: item
        for item in run.results
        if item.metadata["benchmark_case_id"] == "reasoning-001"
    }
    assert results_by_provider["provider-a"].status.value == "passed"
    assert results_by_provider["provider-a"].metrics[0].score == 1.0
    assert results_by_provider["provider-b"].status.value == "failed"
    assert results_by_provider["provider-b"].metrics[0].score == 0.5



def test_committed_smoke_dataset_is_valid_and_scoring_is_deterministic():
    dataset_path = Path(__file__).resolve().parents[1] / "evals" / "model-routing-smoke.json"
    cases = _load_dataset(dataset_path)
    assert len(cases) == 6
    assert len({case["id"] for case in cases}) == len(cases)
    assert all(case["task"] is ModelTask.REASONING for case in cases)

    metric = DeterministicBenchmarkMetric()
    exact_case = EvaluationCase(
        name="exact token",
        input="test prompt",
        expected={"kind": "exact_answer", "answer": "GREEN"},
        metadata={"benchmark_threshold": 1.0},
    )
    result = metric.score(exact_case, "GREEN")
    assert result.score == 1.0
    assert result.passed is True

    json_case = EvaluationCase(
        name="structured fields",
        input="test prompt",
        expected={"kind": "json_fields", "fields": {"status": "needs_review", "priority": "high"}},
        metadata={"benchmark_threshold": 1.0},
    )
    json_result = metric.score(json_case, '{"status":"needs_review","priority":"high"}')
    assert json_result.score == 1.0
    assert json_result.passed is True
