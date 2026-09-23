import pytest

from core.models.contracts import ModelRequest, ModelTask
from integrations.model_providers.openai_compatible import (
    ModelProviderConfigurationError,
    ModelProviderRequestError,
    OpenAICompatibleModelProvider,
    OpenAICompatibleSettings,
    build_model_router_from_env,
)


def settings():
    return OpenAICompatibleSettings(
        base_url="https://provider.example/v1", api_key="secret",
        provider_name="test-provider", default_model="test-model"
    )


def test_provider_maps_chat_request():
    captured = {}
    def transport(url, headers, payload, timeout):
        captured.update(url=url, headers=headers, payload=payload, timeout=timeout)
        return {
            "model": "test-model",
            "choices": [{"message": {"content": "hello"}}],
            "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
        }
    response = OpenAICompatibleModelProvider(settings(), transport=transport).generate(
        ModelRequest(task=ModelTask.CHAT, input_text="Hi", temperature=0)
    )
    assert response.text == "hello"
    assert response.provider == "test-provider"
    assert response.usage["total_tokens"] == 6
    assert captured["url"] == "https://provider.example/v1/chat/completions"
    assert captured["payload"]["model"] == "test-model"
    assert captured["payload"]["messages"] == [{"role": "user", "content": "Hi"}]
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert "secret" not in str(captured["payload"])


def test_provider_rejects_embedding_task():
    provider = OpenAICompatibleModelProvider(settings(), transport=lambda *args: {})
    with pytest.raises(ModelProviderRequestError):
        provider.generate(ModelRequest(task=ModelTask.EMBEDDING, input_text="x"))


def test_environment_factory_is_provider_free_when_unconfigured(monkeypatch):
    for name in ("MODEL_PROVIDER_BASE_URL", "MODEL_PROVIDER_API_KEY", "MODEL_PROVIDER_MODEL"):
        monkeypatch.delenv(name, raising=False)
    assert build_model_router_from_env() is None


def test_environment_factory_rejects_partial_configuration(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER_BASE_URL", "https://provider.example/v1")
    monkeypatch.delenv("MODEL_PROVIDER_API_KEY", raising=False)
    monkeypatch.setenv("MODEL_PROVIDER_MODEL", "test-model")
    with pytest.raises(ModelProviderConfigurationError):
        build_model_router_from_env()
