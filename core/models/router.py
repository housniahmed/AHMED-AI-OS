"""Multi-provider model selection, reliability, resilience, and usage intelligence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from time import sleep, time
from typing import Callable
from uuid import UUID, uuid4

from core.models.contracts import ModelRequest, ModelResponse, ModelTask
from core.models.providers import ModelProvider, ModelProviderError
from core.models.resilience import (
    CircuitBreakerPolicy,
    InMemoryProviderHealthStore,
    ProviderHealthState,
    ProviderHealthStore,
    RetryPolicy,
)
from core.models.usage import (
    InMemoryModelUsageStore,
    ModelPricingCatalog,
    ModelUsageRecord,
    ModelUsageStore,
    group_usage,
    summarize_usage,
    ModelUsageAggregate,
)


@dataclass(frozen=True, slots=True)
class ModelRoute:
    task: ModelTask
    provider: str
    model: str
    priority: int = 0


@dataclass(slots=True)
class ProviderRuntimeState(ProviderHealthState):
    pass


class ModelRouter:
    """Route requests with priority, retries, circuit breaking, and usage intelligence."""

    def __init__(
        self,
        providers: dict[str, ModelProvider],
        routes: tuple[ModelRoute, ...],
        *,
        retry_policy: RetryPolicy | None = None,
        circuit_policy: CircuitBreakerPolicy | None = None,
        health_store: ProviderHealthStore | None = None,
        usage_store: ModelUsageStore | None = None,
        pricing_catalog: ModelPricingCatalog | None = None,
        clock: Callable[[], float] = time,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        self.providers = dict(providers)
        self.routes = tuple(routes)
        self.retry_policy = retry_policy or RetryPolicy()
        self.circuit_policy = circuit_policy or CircuitBreakerPolicy()
        self.health_store = health_store or InMemoryProviderHealthStore()
        self.usage_store = usage_store or InMemoryModelUsageStore()
        self.pricing_catalog = pricing_catalog or ModelPricingCatalog()
        self.clock = clock
        self.sleeper = sleeper
        self._states = {}
        for name in self.providers:
            persisted = self.health_store.load(name)
            self._states[name] = (
                ProviderRuntimeState(**asdict(persisted))
                if persisted
                else ProviderRuntimeState()
            )

    def register_provider(self, provider: ModelProvider) -> None:
        if not provider.name:
            raise ValueError("provider name is required")
        if provider.name in self.providers:
            raise ValueError(f"provider already registered: {provider.name}")
        self.providers[provider.name] = provider
        persisted = self.health_store.load(provider.name)
        self._states[provider.name] = (
            ProviderRuntimeState(**asdict(persisted))
            if persisted
            else ProviderRuntimeState()
        )

    def remove_provider(self, provider_name: str) -> None:
        if provider_name not in self.providers:
            raise KeyError(provider_name)
        del self.providers[provider_name]
        self._states.pop(provider_name, None)
        self.routes = tuple(r for r in self.routes if r.provider != provider_name)

    def set_provider_enabled(self, provider_name: str, enabled: bool) -> None:
        if provider_name not in self.providers:
            raise KeyError(provider_name)
        self._states[provider_name].enabled = enabled
        self._persist(provider_name)

    def add_route(self, route: ModelRoute) -> None:
        if route.provider not in self.providers:
            raise KeyError(f"provider not registered: {route.provider}")
        if not route.model:
            raise ValueError("route model is required")
        self.routes = tuple((*self.routes, route))

    def remove_route(self, *, task: ModelTask, provider: str, model: str) -> None:
        self.routes = tuple(
            r
            for r in self.routes
            if not (r.task == task and r.provider == provider and r.model == model)
        )

    def provider_status(self) -> dict[str, ProviderRuntimeState]:
        return {
            name: ProviderRuntimeState(**asdict(state))
            for name, state in self._states.items()
        }

    def route(self, request: ModelRequest) -> ModelRoute:
        candidates = self._candidates(request)
        if not candidates:
            raise LookupError(f"no model route for task={request.task.value}")
        return candidates[0]

    def usage_records(self) -> tuple[ModelUsageRecord, ...]:
        """Return all recorded provider attempts."""
        return self.usage_store.records()

    def usage_summary(self) -> ModelUsageAggregate:
        return summarize_usage(self.usage_store.records())

    def usage_summary_by_provider(self) -> dict[str, ModelUsageAggregate]:
        return group_usage(self.usage_store.records(), dimension="provider")

    def usage_summary_by_model(self) -> dict[str, ModelUsageAggregate]:
        return group_usage(self.usage_store.records(), dimension="model")

    def usage_summary_by_task(self) -> dict[str, ModelUsageAggregate]:
        return group_usage(self.usage_store.records(), dimension="task")

    def _candidates(self, request: ModelRequest) -> list[ModelRoute]:
        candidates = [
            r
            for r in self.routes
            if r.task == request.task
            and r.provider in self.providers
            and self._eligible(r.provider)
        ]
        if request.model:
            candidates = [r for r in candidates if r.model == request.model]
        return sorted(candidates, key=lambda r: r.priority, reverse=True)

    def _eligible(self, provider_name: str) -> bool:
        state = self._states[provider_name]
        if not state.enabled:
            return False
        if not state.circuit_open:
            return True
        if state.cooldown_until is not None and self.clock() >= state.cooldown_until:
            state.circuit_open = False
            state.opened_at = None
            state.cooldown_until = None
            state.consecutive_failures = 0
            self._persist(provider_name)
            return True
        return False

    def generate(self, request: ModelRequest) -> ModelResponse:
        candidates = self._candidates(request)
        if not candidates:
            raise LookupError(f"no model route for task={request.task.value}")

        request_id = uuid4()
        errors: list[str] = []

        for route_index, route in enumerate(candidates):
            routed = ModelRequest(
                request.task,
                request.messages,
                request.input_text,
                route.model,
                request.max_tokens,
                request.temperature,
                request.metadata,
            )
            for attempt in range(1, self.retry_policy.max_attempts + 1):
                started_at = self.clock()
                try:
                    response = self.providers[route.provider].generate(routed)
                except ModelProviderError as exc:
                    ended_at = self.clock()
                    self._record_usage(
                        request_id=request_id,
                        request=routed,
                        provider=route.provider,
                        model=route.model,
                        response_usage={},
                        started_at=started_at,
                        ended_at=ended_at,
                        success=False,
                        fallback_used=route_index > 0,
                        attempt=attempt,
                        error=str(exc),
                    )
                    self._record_failure(route.provider, exc, now=ended_at)
                    errors.append(f"{route.provider}: attempt {attempt}: {exc}")
                    if (
                        attempt < self.retry_policy.max_attempts
                        and self._should_retry(exc)
                    ):
                        self._backoff(
                            attempt,
                            getattr(exc, "retry_after_seconds", None),
                        )
                        continue
                    break
                else:
                    ended_at = self.clock()
                    self._record_usage(
                        request_id=request_id,
                        request=routed,
                        provider=route.provider,
                        model=response.model or route.model,
                        response_usage=response.usage,
                        started_at=started_at,
                        ended_at=ended_at,
                        success=True,
                        fallback_used=route_index > 0,
                        attempt=attempt,
                    )
                    self._record_success(route.provider, now=ended_at)
                    return response

        raise ModelProviderError(
            f"all eligible model providers failed for task={request.task.value}: "
            + "; ".join(errors)
        )

    def _record_usage(
        self,
        *,
        request_id: UUID,
        request: ModelRequest,
        provider: str,
        model: str,
        response_usage: dict[str, int],
        started_at: float,
        ended_at: float,
        success: bool,
        fallback_used: bool,
        attempt: int,
        error: str | None = None,
    ) -> None:
        prompt_tokens = self._usage_int(
            response_usage,
            "prompt_tokens",
            "input_tokens",
        )
        completion_tokens = self._usage_int(
            response_usage,
            "completion_tokens",
            "output_tokens",
        )
        total_raw = response_usage.get("total_tokens")
        total_tokens = (
            int(total_raw)
            if isinstance(total_raw, (int, float))
            else prompt_tokens + completion_tokens
        )
        tokens_available = bool(
            response_usage
            and any(
                key in response_usage
                for key in (
                    "prompt_tokens",
                    "completion_tokens",
                    "total_tokens",
                    "input_tokens",
                    "output_tokens",
                )
            )
        )
        cost = self.pricing_catalog.estimate(
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        ) if tokens_available else None
        self.usage_store.record(
            ModelUsageRecord(
                request_id=request_id,
                task=request.task,
                provider=provider,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=max(total_tokens, 0),
                tokens_available=tokens_available,
                latency_ms=max((ended_at - started_at) * 1000.0, 0.0),
                success=success,
                fallback_used=fallback_used,
                attempt=attempt,
                estimated_cost_usd=cost,
                error=error,
                metadata={"requested_model": request.model or ""},
            )
        )

    @staticmethod
    def _usage_int(usage: dict[str, int], *keys: str) -> int:
        for key in keys:
            value = usage.get(key)
            if isinstance(value, (int, float)):
                return max(int(value), 0)
        return 0

    def _should_retry(self, error: ModelProviderError) -> bool:
        return bool(getattr(error, "retryable", True))

    def _backoff(self, attempt: int, retry_after_seconds: float | None = None) -> None:
        delay = min(
            self.retry_policy.backoff_seconds * (2 ** max(attempt - 1, 0)),
            self.retry_policy.max_backoff_seconds,
        )
        if retry_after_seconds is not None:
            delay = max(delay, retry_after_seconds)
        if delay > 0:
            self.sleeper(delay)

    def _record_failure(
        self,
        provider_name: str,
        error: Exception,
        *,
        now: float | None = None,
    ) -> None:
        state = self._states[provider_name]
        timestamp = self.clock() if now is None else now
        state.failures += 1
        state.consecutive_failures += 1
        state.last_error = str(error)
        state.last_failure_at = timestamp
        retry_after = getattr(error, "retry_after_seconds", None)
        rate_limited = bool(getattr(error, "rate_limited", False))
        if rate_limited or state.consecutive_failures >= self.circuit_policy.failure_threshold:
            state.circuit_open = True
            state.opened_at = timestamp
            cooldown = self.circuit_policy.cooldown_seconds
            if retry_after is not None:
                cooldown = max(cooldown, retry_after)
            state.cooldown_until = timestamp + cooldown
        self._persist(provider_name)

    def _record_success(self, provider_name: str, *, now: float | None = None) -> None:
        state = self._states[provider_name]
        timestamp = self.clock() if now is None else now
        state.successes += 1
        state.consecutive_failures = 0
        state.last_error = None
        state.last_success_at = timestamp
        state.circuit_open = False
        state.opened_at = None
        state.cooldown_until = None
        self._persist(provider_name)

    def _persist(self, provider_name: str) -> None:
        self.health_store.save(provider_name, self._states[provider_name])
