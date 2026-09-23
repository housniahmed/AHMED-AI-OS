"""Provider interface and deterministic mock provider."""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.models.contracts import ModelRequest, ModelResponse


class ModelProviderError(RuntimeError):
    """Recoverable provider failure that may trigger router fallback."""


class ModelProvider(ABC):
    name: str

    @abstractmethod
    def generate(self, request: ModelRequest) -> ModelResponse:
        raise NotImplementedError


class StaticModelProvider(ModelProvider):
    """Test/dev provider; no network or external model dependency."""

    def __init__(self, name: str, response: str = "") -> None:
        self.name = name
        self.response = response
        self.calls = 0

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.calls += 1
        return ModelResponse(self.response, request.model or self.name, self.name)
