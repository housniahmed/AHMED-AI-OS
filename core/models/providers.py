"""Provider interface and deterministic mock provider."""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.models.contracts import ModelRequest, ModelResponse


class ModelProviderError(RuntimeError):
    """Recoverable provider failure that may trigger router resilience policies."""

    retryable: bool = True
    rate_limited: bool = False
    retry_after_seconds: float | None = None

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = True,
        rate_limited: bool = False,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.rate_limited = rate_limited
        self.retry_after_seconds = retry_after_seconds


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
