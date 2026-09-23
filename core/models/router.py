"""Multi-provider model selection, reliability, and resilience runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from time import sleep, time
from typing import Callable

from core.models.contracts import ModelRequest, ModelResponse, ModelTask
from core.models.providers import ModelProvider, ModelProviderError
from core.models.resilience import (
    CircuitBreakerPolicy,
    InMemoryProviderHealthStore,
    ProviderHealthState,
    ProviderHealthStore,
    RetryPolicy,
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
    """Route requests with priority, retries, circuit breaking, and durable health state."""

    def __init__(
        self,
        providers: dict[str, ModelProvider],
        routes: tuple[ModelRoute, ...],
        *,
        retry_policy: RetryPolicy | None = None,
        circuit_policy: CircuitBreakerPolicy | None = None,
        health_store: ProviderHealthStore | None = None,
        clock: Callable[[], float] = time,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        self.providers = dict(providers)
        self.routes = tuple(routes)
        self.retry_policy = retry_policy or RetryPolicy()
        self.circuit_policy = circuit_policy or CircuitBreakerPolicy()
        self.health_store = health_store or InMemoryProviderHealthStore()
        self.clock = clock
        self.sleeper = sleeper
        self._states = {}
        for name in self.providers:
            persisted = self.health_store.load(name)
            self._states[name] = ProviderRuntimeState(**asdict(persisted)) if persisted else ProviderRuntimeState()

    def register_provider(self, provider: ModelProvider) -> None:
        if not provider.name:
            raise ValueError("provider name is required")
        if provider.name in self.providers:
            raise ValueError(f"provider already registered: {provider.name}")
        self.providers[provider.name] = provider
        persisted = self.health_store.load(provider.name)
        self._states[provider.name] = ProviderRuntimeState(**asdict(persisted)) if persisted else ProviderRuntimeState()

    def remove_provider(self, provider_name: str) -> None:
        if provider_name not in self.providers:
            raise KeyError(provider_name)
        del self.providers[provider_name]
        self._states.pop(provider_name, None)
        self.routes = tuple(r for r in self.routes if r.provider != provider_name)

    def set_provider_enabled(self, provider_name: str, enabled: bool) -> None:
        if provider_name not in self.providers:
            raise KeyError(provider_name)
        state = self._states[provider_name]
        state.enabled = enabled
        self._persist(provider_name)

    def add_route(self, route: ModelRoute) -> None:
        if route.provider not in self.providers:
            raise KeyError(f"provider not registered: {route.provider}")
        if not route.model:
            raise ValueError("route model is required")
        self.routes = tuple((*self.routes, route))

    def remove_route(self, *, task: ModelTask, provider: str, model: str) -> None:
        self.routes = tuple(r for r in self.routes if not (r.task == task and r.provider == provider and r.model == model))

    def provider_status(self) -> dict[str, ProviderRuntimeState]:
        return {name: ProviderRuntimeState(**asdict(state)) for name, state in self._states.items()}

    def route(self, request: ModelRequest) -> ModelRoute:
        candidates = self._candidates(request)
        if not candidates:
            raise LookupError(f"no model route for task={request.task.value}")
        return candidates[0]

    def _candidates(self, request: ModelRequest) -> list[ModelRoute]:
        candidates = [
            r for r in self.routes
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
        cooldown_until = state.cooldown_until
        if cooldown_until is not None and self.clock() >= cooldown_until:
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

        errors: list[str] = []
        for route in candidates:
            provider = self.providers[route.provider]
            routed = ModelRequest(
                request.task, request.messages, request.input_text,
                route.model, request.max_tokens, request.temperature, request.metadata,
            )
            attempts = self.retry_policy.max_attempts
            for attempt in range(1, attempts + 1):
                try:
                    response = provider.generate(routed)
                except ModelProviderError as exc:
                    self._record_failure(route.provider, exc)
                    errors.append(f"{route.provider}: attempt {attempt}: {exc}")
                    if attempt < attempts and self._should_retry(exc):
                        self._backoff(attempt)
                        continue
                    break
                else:
                    self._record_success(route.provider)
                    return response

        raise ModelProviderError(
            f"all eligible model providers failed for task={request.task.value}: " + "; ".join(errors)
        )

    def _should_retry(self, error: ModelProviderError) -> bool:
        return bool(getattr(error, "retryable", True))

    def _backoff(self, attempt: int) -> None:
        delay = min(
            self.retry_policy.backoff_seconds * (2 ** max(attempt - 1, 0)),
            self.retry_policy.max_backoff_seconds,
        )
        if delay > 0:
            self.sleeper(delay)

    def _record_failure(self, provider_name: str, error: Exception) -> None:
        state = self._states[provider_name]
        state.failures += 1
        state.consecutive_failures += 1
        state.last_error = str(error)
        state.last_failure_at = self.clock()
        if state.consecutive_failures >= self.circuit_policy.failure_threshold:
            state.circuit_open = True
            state.opened_at = self.clock()
            state.cooldown_until = self.clock() + self.circuit_policy.cooldown_seconds
        self._persist(provider_name)

    def _record_success(self, provider_name: str) -> None:
        state = self._states[provider_name]
        state.successes += 1
        state.consecutive_failures = 0
        state.last_error = None
        state.last_success_at = self.clock()
        state.circuit_open = False
        state.opened_at = None
        state.cooldown_until = None
        self._persist(provider_name)

    def _persist(self, provider_name: str) -> None:
        self.health_store.save(provider_name, self._states[provider_name])
