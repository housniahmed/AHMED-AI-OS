"""Adaptive model routing policy for AHMED AI OS.

B41 converts B39 reliability state and B40 usage telemetry into an explicit,
explainable routing decision. It never executes tools or changes governance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from core.models.contracts import ModelTask
from core.models.usage import ModelUsageAggregate, summarize_usage

if TYPE_CHECKING:
    from core.models.router import ModelRoute, ProviderRuntimeState


@dataclass(frozen=True, slots=True)
class AdaptiveRoutingPolicy:
    """Weighted routing policy with optional hard constraints."""

    reliability_weight: float = 0.35
    latency_weight: float = 0.25
    quality_weight: float = 0.25
    cost_weight: float = 0.15
    min_reliability: float | None = None
    max_latency_ms: float | None = None
    max_cost_usd_per_attempt: float | None = None
    default_quality: float = 0.5
    unknown_cost_score: float = 0.5

    def __post_init__(self) -> None:
        weights = (
            self.reliability_weight,
            self.latency_weight,
            self.quality_weight,
            self.cost_weight,
        )
        if any(weight < 0 for weight in weights):
            raise ValueError("routing weights must be >= 0")
        if sum(weights) <= 0:
            raise ValueError("at least one routing weight must be > 0")
        if not 0 <= self.default_quality <= 1:
            raise ValueError("default_quality must be between 0 and 1")
        if not 0 <= self.unknown_cost_score <= 1:
            raise ValueError("unknown_cost_score must be between 0 and 1")
        if self.min_reliability is not None and not 0 <= self.min_reliability <= 1:
            raise ValueError("min_reliability must be between 0 and 1")
        if self.max_latency_ms is not None and self.max_latency_ms <= 0:
            raise ValueError("max_latency_ms must be > 0")
        if self.max_cost_usd_per_attempt is not None and self.max_cost_usd_per_attempt < 0:
            raise ValueError("max_cost_usd_per_attempt must be >= 0")

    @property
    def normalized_weights(self) -> tuple[float, float, float, float]:
        total = (
            self.reliability_weight
            + self.latency_weight
            + self.quality_weight
            + self.cost_weight
        )
        return tuple(weight / total for weight in (
            self.reliability_weight,
            self.latency_weight,
            self.quality_weight,
            self.cost_weight,
        ))


@dataclass(frozen=True, slots=True)
class QualitySignal:
    provider: str
    model: str
    task: ModelTask
    score: float
    sample_size: int = 1
    source: str = "external_evaluator"

    def __post_init__(self) -> None:
        if not self.provider or not self.model:
            raise ValueError("quality provider and model are required")
        if not 0 <= self.score <= 1:
            raise ValueError("quality score must be between 0 and 1")
        if self.sample_size < 1:
            raise ValueError("quality sample_size must be >= 1")


class QualitySignalStore(Protocol):
    def get(self, provider: str, model: str, task: ModelTask) -> QualitySignal | None: ...

    def set(self, signal: QualitySignal) -> None: ...


class InMemoryQualitySignalStore(QualitySignalStore):
    def __init__(self) -> None:
        self._signals: dict[tuple[str, str, ModelTask], QualitySignal] = {}

    def get(self, provider: str, model: str, task: ModelTask) -> QualitySignal | None:
        return (
            self._signals.get((provider, model, task))
            or self._signals.get((provider, "*", task))
            or self._signals.get(("*", model, task))
            or self._signals.get(("*", "*", task))
        )

    def set(self, signal: QualitySignal) -> None:
        self._signals[(signal.provider, signal.model, signal.task)] = signal


@dataclass(frozen=True, slots=True)
class RouteScore:
    route: ModelRoute
    total: float
    reliability: float
    latency: float
    quality: float
    cost: float
    observed_reliability: float | None
    average_latency_ms: float | None
    average_cost_usd: float | None
    quality_observed: bool
    eligible: bool
    exclusion_reason: str | None = None


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    selected: ModelRoute
    ranked: tuple[RouteScore, ...]
    policy: AdaptiveRoutingPolicy
    reason: str


class AdaptiveRoutingEngine:
    """Score and rank routes using B39/B40 evidence plus explicit quality signals."""

    def __init__(
        self,
        policy: AdaptiveRoutingPolicy | None = None,
        quality_store: QualitySignalStore | None = None,
    ) -> None:
        self.policy = policy or AdaptiveRoutingPolicy()
        self.quality_store = quality_store or InMemoryQualitySignalStore()

    def choose(
        self,
        routes: list[ModelRoute],
        *,
        states: dict[str, ProviderRuntimeState],
        usage_records,
        task: ModelTask,
    ) -> RoutingDecision:
        scored = [
            self.score(
                route,
                state=states[route.provider],
                usage=summarize_usage(
                    record
                    for record in usage_records
                    if record.provider == route.provider
                    and record.model == route.model
                    and record.task == task
                ),
                task=task,
            )
            for route in routes
        ]
        eligible = [item for item in scored if item.eligible]
        if not eligible:
            raise LookupError(
                f"no route satisfies adaptive policy for task={task.value}"
            )

        ranked = tuple(
            sorted(
                eligible,
                key=lambda item: (item.total, item.route.priority),
                reverse=True,
            )
        )
        selected = ranked[0].route
        quality_text = (
            "observed quality"
            if ranked[0].quality_observed
            else "default quality prior"
        )
        reason = (
            f"selected {selected.provider}/{selected.model} using weighted "
            f"reliability={ranked[0].reliability:.3f}, latency={ranked[0].latency:.3f}, "
            f"quality={ranked[0].quality:.3f} ({quality_text}), cost={ranked[0].cost:.3f}; "
            f"total={ranked[0].total:.3f}"
        )
        return RoutingDecision(
            selected=selected,
            ranked=ranked,
            policy=self.policy,
            reason=reason,
        )

    def score(
        self,
        route: ModelRoute,
        *,
        state: ProviderRuntimeState,
        usage: ModelUsageAggregate,
        task: ModelTask,
    ) -> RouteScore:
        observed_attempts = state.successes + state.failures
        observed_reliability = (
            state.successes / observed_attempts if observed_attempts else None
        )
        reliability = (
            observed_reliability if observed_reliability is not None else 0.5
        )

        average_latency = usage.average_latency_ms if usage.attempts else None
        latency = (
            1.0 / (1.0 + average_latency / 1000.0)
            if average_latency is not None
            else 0.5
        )

        signal = self.quality_store.get(route.provider, route.model, task)
        quality_observed = signal is not None
        quality = signal.score if signal is not None else self.policy.default_quality

        priced_attempts = usage.priced_attempts
        average_cost = (
            usage.estimated_cost_usd / priced_attempts
            if priced_attempts
            else None
        )
        cost = (
            1.0 / (1.0 + max(average_cost, 0.0) * 100.0)
            if average_cost is not None
            else self.policy.unknown_cost_score
        )

        exclusion_reason = None
        if (
            self.policy.min_reliability is not None
            and reliability < self.policy.min_reliability
        ):
            exclusion_reason = (
                f"reliability {reliability:.3f} below minimum "
                f"{self.policy.min_reliability:.3f}"
            )
        elif (
            self.policy.max_latency_ms is not None
            and average_latency is not None
            and average_latency > self.policy.max_latency_ms
        ):
            exclusion_reason = (
                f"latency {average_latency:.1f}ms above maximum "
                f"{self.policy.max_latency_ms:.1f}ms"
            )
        elif (
            self.policy.max_cost_usd_per_attempt is not None
            and average_cost is not None
            and average_cost > self.policy.max_cost_usd_per_attempt
        ):
            exclusion_reason = (
                f"average cost USD {average_cost:.8f} above maximum "
                f"USD {self.policy.max_cost_usd_per_attempt:.8f}"
            )

        rw, lw, qw, cw = self.policy.normalized_weights
        total = rw * reliability + lw * latency + qw * quality + cw * cost
        return RouteScore(
            route=route,
            total=total,
            reliability=reliability,
            latency=latency,
            quality=quality,
            cost=cost,
            observed_reliability=observed_reliability,
            average_latency_ms=average_latency,
            average_cost_usd=average_cost,
            quality_observed=quality_observed,
            eligible=exclusion_reason is None,
            exclusion_reason=exclusion_reason,
        )
