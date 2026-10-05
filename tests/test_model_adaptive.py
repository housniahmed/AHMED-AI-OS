from core.models.adaptive import (
    AdaptiveRoutingEngine,
    AdaptiveRoutingPolicy,
    InMemoryQualitySignalStore,
    QualitySignal,
)
from core.models.contracts import ModelTask
from core.models.resilience import ProviderHealthState
from core.models.router import ModelRoute
from core.models.usage import ModelUsageRecord, summarize_usage


def _state(successes=0, failures=0):
    return ProviderHealthState(successes=successes, failures=failures)


def _usage(provider, model, latency, cost):
    return ModelUsageRecord(
        provider=provider,
        model=model,
        task=ModelTask.CHAT,
        prompt_tokens=1000,
        completion_tokens=100,
        total_tokens=1100,
        tokens_available=True,
        latency_ms=latency,
        estimated_cost_usd=cost,
    )


def test_adaptive_routing_prefers_weighted_best_candidate():
    routes = [
        ModelRoute(ModelTask.CHAT, "cheap", "cheap-model", 100),
        ModelRoute(ModelTask.CHAT, "fast", "fast-model", 50),
    ]
    usage = [
        _usage("cheap", "cheap-model", 900, 0.0001),
        _usage("fast", "fast-model", 100, 0.003),
    ]
    states = {
        "cheap": _state(successes=99, failures=1),
        "fast": _state(successes=99, failures=1),
    }
    quality = InMemoryQualitySignalStore()
    quality.set(QualitySignal("cheap", "cheap-model", ModelTask.CHAT, 0.85))
    quality.set(QualitySignal("fast", "fast-model", ModelTask.CHAT, 0.60))
    engine = AdaptiveRoutingEngine(
        AdaptiveRoutingPolicy(
            reliability_weight=0.30,
            latency_weight=0.20,
            quality_weight=0.35,
            cost_weight=0.15,
        ),
        quality,
    )
    decision = engine.choose(routes, states=states, usage_records=usage, task=ModelTask.CHAT)
    assert decision.selected.provider == "cheap"
    assert len(decision.ranked) == 2
    assert decision.ranked[0].quality_observed is True


def test_adaptive_policy_can_exclude_unreliable_provider():
    routes = [
        ModelRoute(ModelTask.CHAT, "bad", "bad-model", 100),
        ModelRoute(ModelTask.CHAT, "good", "good-model", 10),
    ]
    engine = AdaptiveRoutingEngine(
        AdaptiveRoutingPolicy(min_reliability=0.95)
    )
    decision = engine.choose(
        routes,
        states={"bad": _state(successes=5, failures=5), "good": _state(successes=99, failures=1)},
        usage_records=[],
        task=ModelTask.CHAT,
    )
    assert decision.selected.provider == "good"


def test_quality_is_neutral_when_not_observed():
    route = ModelRoute(ModelTask.CHAT, "provider", "model")
    score = AdaptiveRoutingEngine().score(
        route,
        state=_state(successes=8, failures=2),
        usage=summarize_usage([]),
        task=ModelTask.CHAT,
    )
    assert score.quality == 0.5
    assert score.quality_observed is False


def test_cost_and_latency_are_used_from_b40_usage():
    route = ModelRoute(ModelTask.CHAT, "provider", "model")
    score = AdaptiveRoutingEngine(
        AdaptiveRoutingPolicy(
            reliability_weight=0,
            latency_weight=0.5,
            quality_weight=0,
            cost_weight=0.5,
        )
    ).score(
        route,
        state=_state(successes=1),
        usage=summarize_usage([_usage("provider", "model", 100, 0.001)]),
        task=ModelTask.CHAT,
    )
    assert score.average_latency_ms == 100
    assert score.average_cost_usd == 0.001
    assert 0 < score.latency < 1
    assert 0 < score.cost < 1
