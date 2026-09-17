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
