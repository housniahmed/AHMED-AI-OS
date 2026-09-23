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
