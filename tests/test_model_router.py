import pytest

from core.models.contracts import ModelRequest, ModelTask
from core.models.providers import StaticModelProvider
from core.models.router import ModelRoute, ModelRouter


def test_router_selects_highest_priority_route():
    fast = StaticModelProvider("fast", "fast result")
    deep = StaticModelProvider("deep", "deep result")
    router = ModelRouter(
        {"fast": fast, "deep": deep},
        (ModelRoute(ModelTask.REASONING, "fast", "fast-model", 1),
         ModelRoute(ModelTask.REASONING, "deep", "deep-model", 10)),
    )
    response = router.generate(ModelRequest(ModelTask.REASONING, input_text="solve"))
    assert response.provider == "deep"
    assert response.model == "deep-model"
    assert deep.calls == 1
    assert fast.calls == 0


def test_router_fails_without_route():
    router = ModelRouter({}, ())
    with pytest.raises(LookupError):
        router.generate(ModelRequest(ModelTask.CHAT, input_text="hello"))


def test_router_honors_explicit_model():
    provider = StaticModelProvider("provider", "ok")
    router = ModelRouter(
        {"provider": provider},
        (ModelRoute(ModelTask.CHAT, "provider", "model-a", 1),
         ModelRoute(ModelTask.CHAT, "provider", "model-b", 2)),
    )
    response = router.generate(ModelRequest(ModelTask.CHAT, input_text="hello", model="model-a"))
    assert response.model == "model-a"

from core.models.providers import ModelProviderError
from core.models.resilience import RetryPolicy

def test_router_falls_back_after_recoverable_provider_error():
    class FailingProvider(ModelProvider):
        def __init__(self):
            self.name = "primary"
            self.calls = 0
        def generate(self, request):
            self.calls += 1
            raise ModelProviderError("temporary outage")

    primary = FailingProvider()
    backup = StaticModelProvider("backup", "backup result")
    router = ModelRouter(
        {"primary": primary, "backup": backup},
        (ModelRoute(ModelTask.CHAT, "primary", "primary-model", 100),
         ModelRoute(ModelTask.CHAT, "backup", "backup-model", 50)),
        retry_policy=RetryPolicy(max_attempts=1),
    )
    response = router.generate(ModelRequest(ModelTask.CHAT, input_text="hello"))
    assert response.provider == "backup"
    assert primary.calls == 1
    assert router.provider_status()["primary"].failures == 1

def test_router_can_disable_provider():
    provider = StaticModelProvider("provider", "ok")
    router = ModelRouter({"provider": provider}, (ModelRoute(ModelTask.CHAT, "provider", "model"),))
    router.set_provider_enabled("provider", False)
    with pytest.raises(LookupError):
        router.generate(ModelRequest(ModelTask.CHAT, input_text="hello"))

def test_router_can_manage_providers_and_routes():
    provider = StaticModelProvider("new", "ok")
    router = ModelRouter({}, ())
    router.register_provider(provider)
    router.add_route(ModelRoute(ModelTask.CHAT, "new", "model"))
    assert router.route(ModelRequest(ModelTask.CHAT, input_text="hello")).provider == "new"
    router.remove_provider("new")
    with pytest.raises(LookupError):
        router.route(ModelRequest(ModelTask.CHAT, input_text="hello"))


def test_router_can_use_adaptive_policy_from_historical_runtime_data():
    from core.models.adaptive import (
        AdaptiveRoutingEngine,
        AdaptiveRoutingPolicy,
        InMemoryQualitySignalStore,
        QualitySignal,
    )
    from core.models.resilience import InMemoryProviderHealthStore, ProviderHealthState
    from core.models.usage import InMemoryModelUsageStore, ModelUsageRecord

    fast = StaticModelProvider("fast", "fast result")
    reliable = StaticModelProvider("reliable", "reliable result")
    health = InMemoryProviderHealthStore()
    health.save("fast", ProviderHealthState(successes=90, failures=10))
    health.save("reliable", ProviderHealthState(successes=99, failures=1))

    usage = InMemoryModelUsageStore()
    usage.record(ModelUsageRecord(
        provider="fast", model="fast-model", task=ModelTask.REASONING,
        prompt_tokens=100, completion_tokens=50, total_tokens=150,
        tokens_available=True, latency_ms=80, estimated_cost_usd=0.004,
    ))
    usage.record(ModelUsageRecord(
        provider="reliable", model="reliable-model", task=ModelTask.REASONING,
        prompt_tokens=100, completion_tokens=50, total_tokens=150,
        tokens_available=True, latency_ms=300, estimated_cost_usd=0.001,
    ))

    quality = InMemoryQualitySignalStore()
    quality.set(QualitySignal("fast", "fast-model", ModelTask.REASONING, 0.70))
    quality.set(QualitySignal("reliable", "reliable-model", ModelTask.REASONING, 0.95))
    adaptive = AdaptiveRoutingEngine(
        AdaptiveRoutingPolicy(
            reliability_weight=0.45,
            latency_weight=0.15,
            quality_weight=0.30,
            cost_weight=0.10,
        ),
        quality,
    )
    router = ModelRouter(
        {"fast": fast, "reliable": reliable},
        (
            ModelRoute(ModelTask.REASONING, "fast", "fast-model", 100),
            ModelRoute(ModelTask.REASONING, "reliable", "reliable-model", 50),
        ),
        health_store=health,
        usage_store=usage,
        adaptive_engine=adaptive,
    )

    assert router.route(ModelRequest(ModelTask.REASONING, input_text="solve")).provider == "reliable"
    decision = router.last_routing_decision()
    assert decision is not None
    assert decision.selected.provider == "reliable"
    assert "quality" in decision.reason
