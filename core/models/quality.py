"""B42 model quality intelligence and evaluation feedback."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable, Protocol

from core.evaluation.models import EvaluationRun, EvaluationStatus
from core.models.adaptive import QualitySignal
from core.models.contracts import ModelTask


@dataclass(frozen=True, slots=True)
class QualityObservation:
    provider: str
    model: str
    task: ModelTask
    score: float
    sample_size: int
    pass_rate: float
    metric_scores: dict[str, float] = field(default_factory=dict)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "b42_evaluation"

    def __post_init__(self) -> None:
        if not self.provider or not self.model:
            raise ValueError("provider and model are required")
        if not 0 <= self.score <= 1:
            raise ValueError("quality score must be between 0 and 1")
        if self.sample_size < 1:
            raise ValueError("sample_size must be >= 1")
        if not 0 <= self.pass_rate <= 1:
            raise ValueError("pass_rate must be between 0 and 1")


class QualityObservationStore(Protocol):
    def add(self, observation: QualityObservation) -> None: ...
    def history(self, provider: str, model: str, task: ModelTask) -> tuple[QualityObservation, ...]: ...


class InMemoryQualityObservationStore(QualityObservationStore):
    def __init__(self) -> None:
        self._items: list[QualityObservation] = []

    def add(self, observation: QualityObservation) -> None:
        self._items.append(observation)

    def history(self, provider: str, model: str, task: ModelTask) -> tuple[QualityObservation, ...]:
        return tuple(
            item for item in self._items
            if item.provider == provider and item.model == model and item.task == task
        )


@dataclass(frozen=True, slots=True)
class QualityFeedbackPolicy:
    """Controls how evaluation evidence becomes a routing quality signal."""

    min_samples: int = 1
    recency_weight: float = 0.7
    metric_weights: dict[str, float] = field(default_factory=dict)
    include_failed_results: bool = True

    def __post_init__(self) -> None:
        if self.min_samples < 1:
            raise ValueError("min_samples must be >= 1")
        if not 0 <= self.recency_weight <= 1:
            raise ValueError("recency_weight must be between 0 and 1")
        if any(weight < 0 for weight in self.metric_weights.values()):
            raise ValueError("metric weights must be >= 0")


@dataclass(frozen=True, slots=True)
class QualityProfile:
    provider: str
    model: str
    task: ModelTask
    score: float
    confidence: float
    sample_size: int
    pass_rate: float
    trend: float
    observations: tuple[QualityObservation, ...] = ()


class QualityFeedbackEngine:
    """Turn B32 evaluation runs into explicit, bounded quality evidence for B41."""

    def __init__(
        self,
        store: QualityObservationStore | None = None,
        policy: QualityFeedbackPolicy | None = None,
    ) -> None:
        self.store = store or InMemoryQualityObservationStore()
        self.policy = policy or QualityFeedbackPolicy()

    def ingest_run(self, run: EvaluationRun) -> tuple[QualityObservation, ...]:
        groups: dict[tuple[str, str, ModelTask], list[tuple[float, bool]]] = {}
        for result in run.results:
            if result.status is EvaluationStatus.ERROR and not self.policy.include_failed_results:
                continue
            # Provider/model/task are supplied by the evaluation case metadata.
            # EvaluationRun intentionally stays provider-neutral.
            metadata = result.metadata
            if not metadata:
                # Backward-compatible path: output may carry metadata only when a
                # runner explicitly returns it. Never infer a model identity.
                continue
            provider = str(metadata.get("provider", "")).strip()
            model = str(metadata.get("model", "")).strip()
            task_raw = str(metadata.get("task", "")).strip()
            if not provider or not model or not task_raw:
                continue
            try:
                task = ModelTask(task_raw)
            except ValueError:
                continue
            scores = [metric.score for metric in result.metrics]
            if not scores:
                continue
            metric_score = sum(scores) / len(scores)
            groups.setdefault((provider, model, task), []).append(
                (metric_score, result.status is EvaluationStatus.PASSED)
            )

        observations: list[QualityObservation] = []
        for (provider, model, task), values in groups.items():
            score = sum(value for value, _ in values) / len(values)
            pass_rate = sum(1 for _, passed in values if passed) / len(values)
            metric_scores = {}
            observation = QualityObservation(
                provider=provider,
                model=model,
                task=task,
                score=score,
                sample_size=len(values),
                pass_rate=pass_rate,
                metric_scores=metric_scores,
            )
            self.store.add(observation)
            observations.append(observation)
        return tuple(observations)

    def profile(
        self,
        provider: str,
        model: str,
        task: ModelTask,
    ) -> QualityProfile | None:
        history = self.store.history(provider, model, task)
        if not history:
            return None
        total = sum(item.sample_size for item in history)
        if total < self.policy.min_samples:
            return None

        weighted_scores = []
        for item in history:
            weighted_scores.append((item.score, item.sample_size))
        historical = sum(score * samples for score, samples in weighted_scores) / total
        recent = history[-1].score
        score = (
            self.policy.recency_weight * recent
            + (1 - self.policy.recency_weight) * historical
        )

        if len(history) < 2:
            trend = 0.0
        else:
            trend = history[-1].score - history[-2].score

        confidence = min(1.0, total / 100.0)
        pass_rate = sum(item.pass_rate * item.sample_size for item in history) / total
        return QualityProfile(
            provider=provider,
            model=model,
            task=task,
            score=score,
            confidence=confidence,
            sample_size=total,
            pass_rate=pass_rate,
            trend=trend,
            observations=history,
        )

    def to_quality_signal(self, profile: QualityProfile) -> QualitySignal:
        return QualitySignal(
            provider=profile.provider,
            model=profile.model,
            task=profile.task,
            score=profile.score,
            sample_size=profile.sample_size,
            source="b42_evaluation",
        )

    def update_quality_store(self, profile: QualityProfile, quality_store) -> QualitySignal:
        signal = self.to_quality_signal(profile)
        quality_store.set(signal)
        return signal
