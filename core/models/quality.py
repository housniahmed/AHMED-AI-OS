"""Model quality intelligence and B32 evaluation feedback loop.

B42 learns observable quality from B32 evaluation results. Quality is never
inferred from HTTP success, availability, cost, or latency.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

from core.evaluation.models import EvaluationResult, EvaluationRun, EvaluationStatus
from core.models.contracts import ModelTask


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class QualityLearningPolicy:
    alpha: float = 0.25
    prior_score: float = 0.5
    confidence_full_at: int = 5
    metric_weights: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0 < self.alpha <= 1:
            raise ValueError("alpha must be > 0 and <= 1")
        if not 0 <= self.prior_score <= 1:
            raise ValueError("prior_score must be between 0 and 1")
        if self.confidence_full_at < 1:
            raise ValueError("confidence_full_at must be >= 1")
        if any(weight < 0 for weight in self.metric_weights.values()):
            raise ValueError("metric weights must be >= 0")
        if self.metric_weights and sum(self.metric_weights.values()) <= 0:
            raise ValueError("metric weights must contain a positive weight")


@dataclass(frozen=True, slots=True)
class QualityObservation:
    case_id: UUID
    provider: str
    model: str
    task: ModelTask
    model_family: str | None
    score: float
    status: EvaluationStatus
    metric_scores: dict[str, float]
    observed_at: datetime = field(default_factory=utc_now)
    source: str = "b32_evaluation"

    def __post_init__(self) -> None:
        if not self.provider or not self.model:
            raise ValueError("quality observation provider/model are required")
        if not 0 <= self.score <= 1:
            raise ValueError("quality observation score must be between 0 and 1")
        if not self.metric_scores:
            raise ValueError("quality observation requires metric scores")


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
            if item.provider == provider
            and item.model == model
            and item.task == task
        )


@dataclass(frozen=True, slots=True)
class QualityProfile:
    provider: str
    model: str
    task: ModelTask
    model_family: str | None
    score: float
    confidence: float
    sample_size: int
    pass_rate: float
    passed_evaluations: int
    failed_evaluations: int
    trend: float
    last_observed_score: float
    last_observed_at: datetime

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 1:
            raise ValueError("profile score must be between 0 and 1")
        if not 0 <= self.confidence <= 1:
            raise ValueError("profile confidence must be between 0 and 1")
        if self.sample_size < 1:
            raise ValueError("profile sample_size must be >= 1")
        if not 0 <= self.pass_rate <= 1:
            raise ValueError("profile pass_rate must be between 0 and 1")
        if self.passed_evaluations < 0 or self.failed_evaluations < 0:
            raise ValueError("evaluation counts must be >= 0")


class QualityProfileStore(Protocol):
    def get(self, provider: str, model: str, task: ModelTask, model_family: str | None) -> QualityProfile | None: ...
    def save(self, profile: QualityProfile) -> None: ...
    def all(self) -> tuple[QualityProfile, ...]: ...


class InMemoryQualityProfileStore(QualityProfileStore):
    def __init__(self) -> None:
        self._items: dict[tuple[str, str, ModelTask, str | None], QualityProfile] = {}

    def get(self, provider, model, task, model_family):
        return self._items.get((provider, model, task, model_family))

    def save(self, profile):
        self._items[(profile.provider, profile.model, profile.task, profile.model_family)] = profile

    def all(self):
        return tuple(self._items.values())


class JsonFileQualityProfileStore(QualityProfileStore):
    """Durable single-process store for learned B42 quality profiles."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._items: dict[tuple[str, str, ModelTask, str | None], QualityProfile] = {
            (item.provider, item.model, item.task, item.model_family): item
            for item in self._load()
        }

    def get(self, provider, model, task, model_family):
        return self._items.get((provider, model, task, model_family))

    def save(self, profile):
        self._items[(profile.provider, profile.model, profile.task, profile.model_family)] = profile
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = []
        for item in self._items.values():
            raw = asdict(item)
            raw["task"] = item.task.value
            raw["last_observed_at"] = item.last_observed_at.isoformat()
            payload.append(raw)
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def all(self):
        return tuple(self._items.values())

    def _load(self) -> list[QualityProfile]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid quality profile store: {self.path}") from exc
        if not isinstance(payload, list):
            raise ValueError("quality profile store must be a JSON list")

        profiles = []
        for raw in payload:
            try:
                profiles.append(
                    QualityProfile(
                        provider=str(raw["provider"]),
                        model=str(raw["model"]),
                        task=ModelTask(str(raw["task"])),
                        model_family=raw.get("model_family"),
                        score=float(raw["score"]),
                        confidence=float(raw["confidence"]),
                        sample_size=int(raw["sample_size"]),
                        pass_rate=float(raw["pass_rate"]),
                        passed_evaluations=int(raw.get("passed_evaluations", 0)),
                        failed_evaluations=int(raw.get("failed_evaluations", 0)),
                        trend=float(raw["trend"]),
                        last_observed_score=float(raw["last_observed_score"]),
                        last_observed_at=datetime.fromisoformat(str(raw["last_observed_at"])),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("invalid quality profile") from exc
        return profiles


class ModelFamilyResolver(Protocol):
    def resolve(self, *, model: str, metadata: dict[str, Any]) -> str | None: ...


class MetadataOrKnownPrefixFamilyResolver:
    _KNOWN_PREFIXES = (
        "gpt", "claude", "gemini", "llama", "mistral", "qwen",
        "deepseek", "command", "phi", "gemma",
    )

    def resolve(self, *, model, metadata):
        explicit = metadata.get("model_family")
        if isinstance(explicit, str) and explicit.strip():
            return explicit.strip()
        prefix = re.split(r"[-_/.:]+", model.lower(), maxsplit=1)[0]
        return prefix if prefix in self._KNOWN_PREFIXES else None


class ModelQualityIntelligence:
    """Learn B32 metric results into exact-model and model-family profiles."""

    def __init__(
        self,
        *,
        policy: QualityLearningPolicy | None = None,
        observation_store: QualityObservationStore | None = None,
        profile_store: QualityProfileStore | None = None,
        family_resolver: ModelFamilyResolver | None = None,
    ) -> None:
        self.policy = policy or QualityLearningPolicy()
        self.observation_store = observation_store or InMemoryQualityObservationStore()
        self.profile_store = profile_store or InMemoryQualityProfileStore()
        self.family_resolver = family_resolver or MetadataOrKnownPrefixFamilyResolver()

    def ingest_run(self, run: EvaluationRun) -> tuple[QualityObservation, ...]:
        observations: list[QualityObservation] = []
        for result in run.results:
            observation = self._to_observation(result)
            if observation is None:
                continue
            self.observation_store.add(observation)
            observations.append(observation)
            self._update_profile(
                provider=observation.provider,
                model=observation.model,
                task=observation.task,
                model_family=observation.model_family,
                observation=observation,
            )
            if observation.model_family:
                self._update_profile(
                    provider=observation.provider,
                    model="*",
                    task=observation.task,
                    model_family=observation.model_family,
                    observation=observation,
                )
                self._update_profile(
                    provider="*",
                    model="*",
                    task=observation.task,
                    model_family=observation.model_family,
                    observation=observation,
                )
        return tuple(observations)

    def profile(self, provider: str, model: str, task: ModelTask) -> QualityProfile | None:
        exact = self.profile_store.get(provider, model, task, None)
        if exact is not None:
            return exact
        return next(
            (
                item
                for item in self.profile_store.all()
                if item.provider == provider
                and item.model == model
                and item.task == task
            ),
            None,
        )

    def family_profile(self, model_family: str, task: ModelTask, provider: str = "*") -> QualityProfile | None:
        model = "*"
        return self.profile_store.get(provider, model, task, model_family)

    def quality_signals(self) -> tuple[Any, ...]:
        from core.models.adaptive import QualitySignal

        return tuple(
            QualitySignal(
                provider=item.provider,
                model=item.model,
                task=item.task,
                score=item.score,
                sample_size=item.sample_size,
                confidence=item.confidence,
                source="b42_evaluation",
                model_family=item.model_family,
            )
            for item in self.profile_store.all()
        )

    def get(self, provider: str, model: str, task: ModelTask, model_family: str | None = None):
        return self.signal_store().get(
            provider,
            model,
            task,
            model_family=model_family,
        )

    def set(self, signal) -> None:
        self.signal_store().set(signal)

    def signal_store(self):
        return LearnedQualitySignalStore(
            profile_store=self.profile_store,
            prior_score=self.policy.prior_score,
        )

    def _to_observation(self, result: EvaluationResult) -> QualityObservation | None:
        metadata = result.metadata
        provider = str(metadata.get("provider", "")).strip()
        model = str(metadata.get("model", "")).strip()
        task_raw = str(metadata.get("task", "")).strip()
        if not provider or not model or not task_raw or not result.metrics:
            return None
        try:
            task = ModelTask(task_raw)
        except ValueError:
            return None

        metrics = {metric.name: metric.score for metric in result.metrics if metric.name}
        if not metrics:
            return None

        selected = [
            (name, score, self.policy.metric_weights.get(name, 0.0))
            for name, score in metrics.items()
            if name in self.policy.metric_weights
        ]
        if selected and sum(weight for _, _, weight in selected) > 0:
            denominator = sum(weight for _, _, weight in selected)
            score = sum(value * weight for _, value, weight in selected) / denominator
        else:
            score = sum(metrics.values()) / len(metrics)

        family = self.family_resolver.resolve(
            model=model,
            metadata=dict(metadata),
        )
        return QualityObservation(
            case_id=result.case_id,
            provider=provider,
            model=model,
            task=task,
            model_family=family,
            score=score,
            status=result.status,
            metric_scores=metrics,
        )

    def _update_profile(
        self,
        *,
        provider: str,
        model: str,
        task: ModelTask,
        model_family: str | None,
        observation: QualityObservation,
    ) -> None:
        previous = self.profile_store.get(provider, model, task, model_family)
        previous_score = previous.score if previous else self.policy.prior_score
        previous_samples = previous.sample_size if previous else 0
        previous_passed = previous.passed_evaluations if hasattr(previous, "passed_evaluations") else 0
        previous_failed = previous.failed_evaluations if hasattr(previous, "failed_evaluations") else 0
        score = (
            self.policy.alpha * observation.score
            + (1 - self.policy.alpha) * previous_score
        )
        sample_size = previous_samples + 1
        passed = previous_passed + (observation.status is EvaluationStatus.PASSED)
        failed = previous_failed + (observation.status is EvaluationStatus.FAILED)
        trend = (
            observation.score - previous.last_observed_score
            if previous is not None
            else 0.0
        )
        self.profile_store.save(
            QualityProfile(
                provider=provider,
                model=model,
                task=task,
                model_family=model_family,
                score=score,
                confidence=min(1.0, sample_size / self.policy.confidence_full_at),
                sample_size=sample_size,
                pass_rate=passed / sample_size,
                passed_evaluations=passed,
                failed_evaluations=failed,
                trend=trend,
                last_observed_score=observation.score,
                last_observed_at=observation.observed_at,
            )
        )


class LearnedQualitySignalStore:
    """Adapter exposing learned B42 profiles through the B41 signal contract."""

    def __init__(self, *, profile_store: QualityProfileStore, prior_score: float = 0.5) -> None:
        self.profile_store = profile_store
        self.prior_score = prior_score

    def get(self, provider: str, model: str, task: ModelTask, model_family: str | None = None):
        profile = self.profile_store.get(provider, model, task, None)
        if profile is None:
            profile = next(
                (
                    item
                    for item in self.profile_store.all()
                    if item.provider == provider
                    and item.model == model
                    and item.task == task
                ),
                None,
            )
        if profile is None and model_family:
            profile = self.profile_store.get(provider, "*", task, model_family)
        if profile is None and model_family:
            profile = self.profile_store.get("*", "*", task, model_family)
        if profile is None:
            return None

        from core.models.adaptive import QualitySignal

        return QualitySignal(
            provider=profile.provider,
            model=profile.model,
            task=profile.task,
            score=profile.score,
            sample_size=profile.sample_size,
            confidence=profile.confidence,
            source="b42_evaluation",
            model_family=profile.model_family,
        )

    def set(self, signal):
        self.profile_store.save(
            QualityProfile(
                provider=signal.provider,
                model=signal.model,
                task=signal.task,
                model_family=getattr(signal, "model_family", None),
                score=signal.score,
                confidence=getattr(signal, "confidence", 1.0),
                sample_size=max(signal.sample_size, 1),
                pass_rate=signal.score,
                passed_evaluations=0,
                failed_evaluations=0,
                trend=0.0,
                last_observed_score=signal.score,
                last_observed_at=utc_now(),
            )
        )
