from uuid import uuid4

from core.evaluation.models import EvaluationCase, EvaluationResult, EvaluationRun, EvaluationStatus, MetricResult
from core.models.contracts import ModelTask
from core.models.quality import QualityFeedbackEngine, QualityFeedbackPolicy, InMemoryQualityObservationStore


def _run(score: float, passed: bool):
    case_id = uuid4()
    result = EvaluationResult(
        case_id=case_id,
        status=EvaluationStatus.PASSED if passed else EvaluationStatus.FAILED,
        metrics=(MetricResult("quality", score, passed, 0.8),),
    )
    # B42 accepts provider/model/task identity from the result metadata boundary.
    result_with_metadata = result
    result_with_metadata = type(result)(
        case_id=result.case_id,
        status=result.status,
        metrics=result.metrics,
        output={"answer": "ok"},
        metadata={"provider": "p", "model": "m", "task": "reasoning"},
    )
    return EvaluationRun(results=(result_with_metadata,))


def test_quality_feedback_requires_explicit_identity():
    engine = QualityFeedbackEngine()
    run = EvaluationRun(results=(
        EvaluationResult(
            case_id=uuid4(),
            status=EvaluationStatus.PASSED,
            metrics=(MetricResult("quality", 1.0, True),),
        ),
    ))
    assert engine.ingest_run(run) == ()


def test_quality_profile_uses_recent_and_historical_evidence():
    store = InMemoryQualityObservationStore()
    engine = QualityFeedbackEngine(
        store,
        QualityFeedbackPolicy(min_samples=1, recency_weight=0.5),
    )
    engine.store.add(__import__("core.models.quality", fromlist=["QualityObservation"]).QualityObservation(
        provider="p", model="m", task=ModelTask.REASONING,
        score=0.6, sample_size=10, pass_rate=0.6,
    ))
    engine.store.add(__import__("core.models.quality", fromlist=["QualityObservation"]).QualityObservation(
        provider="p", model="m", task=ModelTask.REASONING,
        score=0.9, sample_size=10, pass_rate=0.9,
    ))
    profile = engine.profile("p", "m", ModelTask.REASONING)
    assert profile is not None
    assert 0.74 < profile.score < 0.76
    assert profile.trend == 0.3
    assert profile.sample_size == 20


def test_profile_can_become_b41_quality_signal():
    store = InMemoryQualityObservationStore()
    engine = QualityFeedbackEngine(store)
    store.add(__import__("core.models.quality", fromlist=["QualityObservation"]).QualityObservation(
        provider="p", model="m", task=ModelTask.CHAT,
        score=0.88, sample_size=20, pass_rate=0.9,
    ))
    profile = engine.profile("p", "m", ModelTask.CHAT)
    signal = engine.to_quality_signal(profile)
    assert signal.score == 0.88
    assert signal.sample_size == 20
    assert signal.source == "b42_evaluation"

def test_evaluation_run_becomes_quality_observation():
    engine = QualityFeedbackEngine()
    run = EvaluationRun(results=(
        EvaluationResult(
            case_id=uuid4(),
            status=EvaluationStatus.PASSED,
            metrics=(MetricResult("quality", 0.9, True),),
            metadata={"provider":"p","model":"m","task":"reasoning"},
        ),
        EvaluationResult(
            case_id=uuid4(),
            status=EvaluationStatus.FAILED,
            metrics=(MetricResult("quality", 0.5, False),),
            metadata={"provider":"p","model":"m","task":"reasoning"},
        ),
    ))
    observations = engine.ingest_run(run)
    assert len(observations) == 1
    assert observations[0].score == 0.7
    assert observations[0].pass_rate == 0.5
