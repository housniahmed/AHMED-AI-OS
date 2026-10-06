import tempfile
from pathlib import Path
from uuid import uuid4

from core.evaluation.models import EvaluationResult, EvaluationRun, EvaluationStatus, MetricResult
from core.models.adaptive import AdaptiveRoutingEngine
from core.models.contracts import ModelTask
from core.models.quality import (
    JsonFileQualityProfileStore,
    MetadataOrKnownPrefixFamilyResolver,
    ModelQualityIntelligence,
    QualityLearningPolicy,
)


def _result(
    score: float,
    *,
    provider: str = "provider-a",
    model: str = "gpt-test",
    task: str = "reasoning",
    model_family: str | None = "gpt",
    status: EvaluationStatus | None = None,
):
    metadata = {"provider": provider, "model": model, "task": task}
    if model_family is not None:
        metadata["model_family"] = model_family
    return EvaluationResult(
        case_id=uuid4(),
        status=status or (EvaluationStatus.PASSED if score >= 0.8 else EvaluationStatus.FAILED),
        metrics=(MetricResult("quality", score, score >= 0.8),),
        metadata=metadata,
    )


def test_b42_requires_explicit_model_identity_and_metrics():
    engine = ModelQualityIntelligence()
    run = EvaluationRun(results=(
        EvaluationResult(case_id=uuid4(), status=EvaluationStatus.PASSED),
        EvaluationResult(
            case_id=uuid4(),
            status=EvaluationStatus.PASSED,
            metadata={"provider": "p", "model": "m", "task": "reasoning"},
        ),
    ))
    assert engine.ingest_run(run) == ()


def test_b42_learns_exact_model_and_family_from_b32():
    engine = ModelQualityIntelligence(
        policy=QualityLearningPolicy(alpha=1.0, confidence_full_at=2)
    )
    observations = engine.ingest_run(
        EvaluationRun(results=(_result(0.9), _result(0.7)))
    )
    assert len(observations) == 2

    exact = engine.profile("provider-a", "gpt-test", ModelTask.REASONING)
    family = engine.family_profile("gpt", ModelTask.REASONING)
    assert exact is not None
    assert family is not None
    assert exact.score == 0.7
    assert exact.sample_size == 2
    assert family.score == 0.7
    assert family.sample_size == 2
    assert exact.confidence == 1.0


def test_b42_uses_weighted_metric_evidence():
    engine = ModelQualityIntelligence(
        policy=QualityLearningPolicy(
            alpha=1.0,
            metric_weights={"accuracy": 0.8, "grounding": 0.2},
        )
    )
    run = EvaluationRun(results=(
        EvaluationResult(
            case_id=uuid4(),
            status=EvaluationStatus.FAILED,
            metrics=(
                MetricResult("accuracy", 0.9, False),
                MetricResult("grounding", 0.5, False),
            ),
            metadata={"provider": "p", "model": "m", "task": "chat"},
        ),
    ))
    engine.ingest_run(run)
    profile = engine.profile("p", "m", ModelTask.CHAT)
    assert profile is not None
    assert abs(profile.score - 0.82) < 1e-9


def test_b42_evolves_quality_with_ema_not_static_thresholds():
    engine = ModelQualityIntelligence(
        policy=QualityLearningPolicy(alpha=0.5)
    )
    engine.ingest_run(EvaluationRun(results=(_result(0.9),)))
    first = engine.profile("provider-a", "gpt-test", ModelTask.REASONING)
    engine.ingest_run(EvaluationRun(results=(_result(0.5),)))
    second = engine.profile("provider-a", "gpt-test", ModelTask.REASONING)
    assert first is not None and second is not None
    assert abs(first.score - 0.70) < 1e-9
    assert abs(second.score - 0.60) < 1e-9
    assert second.trend < 0


def test_b42_exposes_quality_signal_with_confidence():
    engine = ModelQualityIntelligence(
        policy=QualityLearningPolicy(confidence_full_at=5)
    )
    engine.ingest_run(EvaluationRun(results=(_result(0.9),)))
    signal = engine.get("provider-a", "gpt-test", ModelTask.REASONING, model_family="gpt")
    assert signal is not None
    assert signal.score > 0.5
    assert signal.confidence == 0.2
    assert signal.model_family == "gpt"
    assert signal.source == "b42_evaluation"


def test_b42_learned_signal_can_feed_b41_directly():
    intelligence = ModelQualityIntelligence(
        policy=QualityLearningPolicy(alpha=1.0)
    )
    intelligence.ingest_run(EvaluationRun(results=(
        _result(0.95),
    )))
    route = __import__("core.models.router", fromlist=["ModelRoute"]).ModelRoute(
        ModelTask.REASONING, "provider-a", "gpt-test"
    )
    state = __import__(
        "core.models.resilience", fromlist=["ProviderHealthState"]
    ).ProviderHealthState(successes=10)
    usage = __import__(
        "core.models.usage", fromlist=["summarize_usage"]
    ).summarize_usage([])
    score = AdaptiveRoutingEngine(quality_store=intelligence).score(
        route,
        state=state,
        usage=usage,
        task=ModelTask.REASONING,
    )
    assert score.quality_observed is True
    assert score.quality_confidence == 0.2
    assert score.quality > 0.5


def test_b42_json_profile_store_is_durable():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "quality.json"
        first = ModelQualityIntelligence(
            profile_store=JsonFileQualityProfileStore(path)
        )
        first.ingest_run(EvaluationRun(results=(_result(0.9),)))
        second = ModelQualityIntelligence(
            profile_store=JsonFileQualityProfileStore(path)
        )
        assert len(second.profiles()) == 3


def test_family_resolver_prefers_explicit_metadata():
    resolver = MetadataOrKnownPrefixFamilyResolver()
    assert resolver.resolve(
        model="some-custom-model",
        metadata={"model_family": "my-family"},
    ) == "my-family"
    assert resolver.resolve(
        model="gpt-5.1",
        metadata={},
    ) == "gpt"
    assert resolver.resolve(
        model="unknown-model",
        metadata={},
    ) is None
