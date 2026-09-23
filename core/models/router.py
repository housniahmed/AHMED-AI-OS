"""Multi-provider model selection, management, and fallback runtime."""

from __future__ import annotations

from dataclasses import dataclass, field

from core.models.contracts import ModelRequest, ModelResponse, ModelTask
from core.models.providers import ModelProvider, ModelProviderError


@dataclass(frozen=True, slots=True)
class ModelRoute:
    task: ModelTask
    provider: str
    model: str
    priority: int = 0


@dataclass(slots=True)
class ProviderRuntimeState:
    enabled: bool = True
    successes: int = 0
    failures: int = 0
    last_error: str | None = None


class ModelRouter:
    """Route requests across managed providers with deterministic fallback."""

    def __init__(self, providers: dict[str, ModelProvider], routes: tuple[ModelRoute, ...]) -> None:
        self.providers = dict(providers)
        self.routes = tuple(routes)
        self._states = {name: ProviderRuntimeState() for name in self.providers}

    def register_provider(self, provider: ModelProvider) -> None:
        if not provider.name:
            raise ValueError("provider name is required")
        if provider.name in self.providers:
            raise ValueError(f"provider already registered: {provider.name}")
        self.providers[provider.name] = provider
        self._states[provider.name] = ProviderRuntimeState()

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

    def add_route(self, route: ModelRoute) -> None:
        if route.provider not in self.providers:
            raise KeyError(f"provider not registered: {route.provider}")
        if not route.model:
            raise ValueError("route model is required")
        self.routes = tuple((*self.routes, route))

    def remove_route(self, *, task: ModelTask, provider: str, model: str) -> None:
        self.routes = tuple(
            r for r in self.routes
            if not (r.task == task and r.provider == provider and r.model == model)
        )

    def provider_status(self) -> dict[str, ProviderRuntimeState]:
        return {
            name: ProviderRuntimeState(
                enabled=state.enabled,
                successes=state.successes,
                failures=state.failures,
                last_error=state.last_error,
            )
            for name, state in self._states.items()
        }

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
            and self._states[r.provider].enabled
        ]
        if request.model:
            candidates = [r for r in candidates if r.model == request.model]
        return sorted(candidates, key=lambda r: r.priority, reverse=True)

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
            try:
                response = provider.generate(routed)
            except ModelProviderError as exc:
                self._record_failure(route.provider, exc)
                errors.append(f"{route.provider}: {exc}")
                continue
            self._record_success(route.provider)
            return response

        raise ModelProviderError(
            f"all model providers failed for task={request.task.value}: " + "; ".join(errors)
        )

    def _record_failure(self, provider_name: str, error: Exception) -> None:
        state = self._states[provider_name]
        state.failures += 1
        state.last_error = str(error)

    def _record_success(self, provider_name: str) -> None:
        state = self._states[provider_name]
        state.successes += 1
        state.last_error = None
