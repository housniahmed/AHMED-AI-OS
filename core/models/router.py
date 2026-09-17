"""Policy-driven model selection and invocation."""

from __future__ import annotations

from dataclasses import dataclass

from core.models.contracts import ModelRequest, ModelResponse, ModelTask
from core.models.providers import ModelProvider


@dataclass(frozen=True, slots=True)
class ModelRoute:
    task: ModelTask
    provider: str
    model: str
    priority: int = 0


class ModelRouter:
    """Route requests by task without exposing provider details to agents."""

    def __init__(self, providers: dict[str, ModelProvider], routes: tuple[ModelRoute, ...]) -> None:
        self.providers = providers
        self.routes = routes

    def route(self, request: ModelRequest) -> ModelRoute:
        candidates = [r for r in self.routes if r.task == request.task and r.provider in self.providers]
        if request.model:
            candidates = [r for r in candidates if r.model == request.model]
        if not candidates:
            raise LookupError(f"no model route for task={request.task.value}")
        return sorted(candidates, key=lambda r: r.priority, reverse=True)[0]

    def generate(self, request: ModelRequest) -> ModelResponse:
        route = self.route(request)
        provider = self.providers[route.provider]
        routed = ModelRequest(request.task, request.messages, request.input_text,
                              route.model, request.max_tokens, request.temperature, request.metadata)
        return provider.generate(routed)
