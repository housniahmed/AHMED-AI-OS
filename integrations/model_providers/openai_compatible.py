"""OpenAI-compatible chat-completions model provider adapter."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from core.models.contracts import ModelRequest, ModelResponse, ModelTask
from core.models.providers import ModelProvider, ModelProviderError
from core.models.router import ModelRoute, ModelRouter


class ModelProviderConfigurationError(ValueError):
    """Raised when external model provider configuration is incomplete."""


class ModelProviderRequestError(ModelProviderError):
    """Raised when the external provider cannot satisfy a model request."""


@dataclass(frozen=True, slots=True)
class OpenAICompatibleSettings:
    base_url: str
    api_key: str
    provider_name: str = "openai-compatible"
    default_model: str = ""
    timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "OpenAICompatibleSettings":
        base_url = os.getenv("MODEL_PROVIDER_BASE_URL", "").strip()
        api_key = os.getenv("MODEL_PROVIDER_API_KEY", "").strip()
        provider_name = os.getenv("MODEL_PROVIDER_NAME", "openai-compatible").strip()
        default_model = os.getenv("MODEL_PROVIDER_MODEL", "").strip()
        timeout_raw = os.getenv("MODEL_PROVIDER_TIMEOUT_SECONDS", "30").strip()
        if not base_url:
            raise ModelProviderConfigurationError("MODEL_PROVIDER_BASE_URL is required")
        if not api_key:
            raise ModelProviderConfigurationError("MODEL_PROVIDER_API_KEY is required")
        if not default_model:
            raise ModelProviderConfigurationError("MODEL_PROVIDER_MODEL is required")
        try:
            timeout = float(timeout_raw)
        except ValueError as exc:
            raise ModelProviderConfigurationError("MODEL_PROVIDER_TIMEOUT_SECONDS must be numeric") from exc
        if timeout <= 0:
            raise ModelProviderConfigurationError("MODEL_PROVIDER_TIMEOUT_SECONDS must be > 0")
        return cls(base_url.rstrip("/"), api_key, provider_name or "openai-compatible", default_model, timeout)


HttpTransport = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]


def _urllib_transport(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ModelProviderRequestError(
            f"model provider HTTP {exc.code}: {detail[:500]}",
            retryable=exc.code in {408, 409, 425, 429} or exc.code >= 500,
            rate_limited=exc.code == 429,
            retry_after_seconds=_retry_after_seconds(exc),
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise ModelProviderRequestError(f"model provider network error: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ModelProviderRequestError("model provider returned invalid JSON") from exc


def _retry_after_seconds(exc: HTTPError) -> float | None:
    raw = exc.headers.get("Retry-After") if exc.headers else None
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        return None


class OpenAICompatibleModelProvider(ModelProvider):
    """Adapter for providers exposing an OpenAI-compatible /chat/completions API."""

    def __init__(self, settings: OpenAICompatibleSettings, *, transport: HttpTransport = _urllib_transport) -> None:
        self.name = settings.provider_name
        self.settings = settings
        self._transport = transport

    def generate(self, request: ModelRequest) -> ModelResponse:
        if request.task == ModelTask.EMBEDDING:
            raise ModelProviderRequestError("OpenAI-compatible chat provider does not implement embeddings")
        model = request.model or self.settings.default_model
        if not model:
            raise ModelProviderRequestError("no model configured for the request")
        messages = list(request.messages) or [{"role": "user", "content": request.input_text}]
        payload: dict[str, Any] = {"model": model, "messages": messages}
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        response = self._transport(
            f"{self.settings.base_url}/chat/completions",
            {"Authorization": f"Bearer {self.settings.api_key}", "Content-Type": "application/json"},
            payload,
            self.settings.timeout_seconds,
        )
        text = self._extract_text(response)
        usage = self._extract_usage(response)
        return ModelResponse(
            text=text,
            model=str(response.get("model") or model),
            provider=self.name,
            usage=usage,
            metadata={"task": request.task.value},
        )

    @staticmethod
    def _extract_text(response: dict[str, Any]) -> str:
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelProviderRequestError("model provider response has no assistant content") from exc
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [item.get("text", "") for item in content if isinstance(item, dict)]
            return "".join(part for part in parts if isinstance(part, str))
        raise ModelProviderRequestError("model provider returned unsupported content format")

    @staticmethod
    def _extract_usage(response: dict[str, Any]) -> dict[str, int]:
        raw = response.get("usage")
        if not isinstance(raw, dict):
            return {}
        return {str(key): int(value) for key, value in raw.items() if isinstance(value, (int, float))}


def _settings_from_prefix(prefix: str) -> OpenAICompatibleSettings:
    def value(name: str, default: str = "") -> str:
        return os.getenv(f"MODEL_PROVIDER_{prefix}_{name}", default).strip()

    base_url = value("BASE_URL")
    api_key = value("API_KEY")
    model = value("MODEL")
    name = value("NAME", prefix.lower())
    timeout_raw = value("TIMEOUT_SECONDS", "30")
    if not base_url or not api_key or not model:
        raise ModelProviderConfigurationError(
            f"incomplete configuration for provider id '{prefix.lower()}'"
        )
    try:
        timeout = float(timeout_raw)
    except ValueError as exc:
        raise ModelProviderConfigurationError(
            f"MODEL_PROVIDER_{prefix}_TIMEOUT_SECONDS must be numeric"
        ) from exc
    if timeout <= 0:
        raise ModelProviderConfigurationError(
            f"MODEL_PROVIDER_{prefix}_TIMEOUT_SECONDS must be > 0"
        )
    return OpenAICompatibleSettings(base_url.rstrip("/"), api_key, name or prefix.lower(), model, timeout)


def build_model_router_from_env() -> ModelRouter | None:
    """Build a single- or multi-provider router from environment configuration."""
    provider_ids = os.getenv("MODEL_PROVIDER_IDS", "").strip()
    if provider_ids:
        providers = {}
        routes = []
        for raw_id in provider_ids.split(","):
            provider_id = raw_id.strip()
            if not provider_id:
                continue
            prefix = provider_id.upper().replace("-", "_")
            settings = _settings_from_prefix(prefix)
            if settings.provider_name in providers:
                raise ModelProviderConfigurationError(
                    f"duplicate provider name: {settings.provider_name}"
                )
            provider = OpenAICompatibleModelProvider(settings)
            providers[provider.name] = provider

            priority_raw = os.getenv(
                f"MODEL_PROVIDER_{prefix}_PRIORITY", "0"
            ).strip()
            try:
                priority = int(priority_raw)
            except ValueError as exc:
                raise ModelProviderConfigurationError(
                    f"MODEL_PROVIDER_{prefix}_PRIORITY must be an integer"
                ) from exc

            tasks_raw = os.getenv(
                f"MODEL_PROVIDER_{prefix}_TASKS", "chat,reasoning"
            )
            for task_name in tasks_raw.split(","):
                task_name = task_name.strip()
                if not task_name:
                    continue
                try:
                    task = ModelTask(task_name)
                except ValueError as exc:
                    raise ModelProviderConfigurationError(
                        f"unsupported model task '{task_name}' for provider '{provider_id}'"
                    ) from exc
                if task == ModelTask.EMBEDDING:
                    raise ModelProviderConfigurationError(
                        f"provider '{provider_id}' does not support embedding routes"
                    )
                routes.append(ModelRoute(task, provider.name, settings.default_model, priority))

        if not providers:
            raise ModelProviderConfigurationError("MODEL_PROVIDER_IDS contains no provider ids")
        return ModelRouter(providers, tuple(routes))

    configured = any(os.getenv(name, "").strip() for name in (
        "MODEL_PROVIDER_BASE_URL", "MODEL_PROVIDER_API_KEY", "MODEL_PROVIDER_MODEL"
    ))
    if not configured:
        return None

    settings = OpenAICompatibleSettings.from_env()
    provider = OpenAICompatibleModelProvider(settings)
    routes = (
        ModelRoute(ModelTask.CHAT, provider.name, settings.default_model),
        ModelRoute(ModelTask.REASONING, provider.name, settings.default_model),
    )
    return ModelRouter({provider.name: provider}, routes)
