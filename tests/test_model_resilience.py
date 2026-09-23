import tempfile
from pathlib import Path

import pytest

from core.models.contracts import ModelRequest, ModelTask
from core.models.providers import ModelProvider, ModelProviderError, StaticModelProvider
from core.models.resilience import (
    CircuitBreakerPolicy,
    InMemoryProviderHealthStore,
    JsonFileProviderHealthStore,
    ProviderHealthState,
    RetryPolicy,
)
from core.models.router import ModelRoute, ModelRouter


class FailingProvider(ModelProvider):
    def __init__(self, name="primary", failures=99):
        self.name = name
        self.remaining = failures
        self.calls = 0

    def generate(self, request):
        self.calls += 1
        if self.remaining:
            self.remaining -= 1
            raise ModelProviderError("temporary failure")
        return StaticModelProvider(self.name, "recovered").generate(request)


def test_retry_policy_retries_before_fallback():
    primary = FailingProvider(failures=1)
    backup = StaticModelProvider("backup", "backup")
    router = ModelRouter(
        {"primary": primary, "backup": backup},
        (ModelRoute(ModelTask.CHAT, "primary", "primary-model", 100),
         ModelRoute(ModelTask.CHAT, "backup", "backup-model", 50)),
        retry_policy=RetryPolicy(max_attempts=2, backoff_seconds=0),
    )
    result = router.generate(ModelRequest(ModelTask.CHAT, input_text="hi"))
    assert result.provider == "primary"
    assert primary.calls == 2


def test_circuit_opens_and_recovers_after_cooldown():
    primary = FailingProvider(failures=3)
    backup = StaticModelProvider("backup", "backup")
    clock = [100.0]
    router = ModelRouter(
        {"primary": primary, "backup": backup},
        (ModelRoute(ModelTask.CHAT, "primary", "p", 100),
         ModelRoute(ModelTask.CHAT, "backup", "b", 50)),
        retry_policy=RetryPolicy(max_attempts=1),
        circuit_policy=CircuitBreakerPolicy(failure_threshold=1, cooldown_seconds=10),
        clock=lambda: clock[0],
    )
    assert router.generate(ModelRequest(ModelTask.CHAT, input_text="x")).provider == "backup"
    assert router.provider_status()["primary"].circuit_open
    primary.remaining = 0
    clock[0] = 111.0
    assert router.generate(ModelRequest(ModelTask.CHAT, input_text="x")).provider == "primary"
    assert not router.provider_status()["primary"].circuit_open


def test_health_state_survives_router_restart():
    store = InMemoryProviderHealthStore()
    provider = FailingProvider(failures=1)
    routes = (ModelRoute(ModelTask.CHAT, "primary", "p", 100),)
    first = ModelRouter({"primary": provider}, routes, retry_policy=RetryPolicy(max_attempts=1), health_store=store)
    with pytest.raises(ModelProviderError):
        first.generate(ModelRequest(ModelTask.CHAT, input_text="x"))
    second = ModelRouter({"primary": provider}, routes, retry_policy=RetryPolicy(max_attempts=1), health_store=store)
    assert second.provider_status()["primary"].failures == 1
    assert second.provider_status()["primary"].consecutive_failures == 1


def test_json_health_store_persists_state():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "health.json"
        store = JsonFileProviderHealthStore(path)
        state = ProviderHealthState(failures=4, circuit_open=True, cooldown_until=123.0)
        store.save("provider", state)
        loaded = JsonFileProviderHealthStore(path).load("provider")
        assert loaded is not None
        assert loaded.failures == 4
        assert loaded.circuit_open is True
