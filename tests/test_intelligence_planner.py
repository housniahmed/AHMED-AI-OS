from core.intelligence.planner import ModelAgentPlanner, PlannerResponseError
from core.models.providers import StaticModelProvider
from core.models.router import ModelRoute, ModelRouter
from core.models.contracts import ModelTask


def make_router(response):
    provider = StaticModelProvider("test", response)
    return ModelRouter({"test": provider}, (ModelRoute(ModelTask.REASONING, "test", "reasoning-test"),))


def test_model_planner_parses_strict_action_contract():
    router = make_router('{"observations":["found context"],"actions":[{"name":"send_message","description":"send a message","level":"execute","arguments":{"text":"hello"}}]}')
    observations, actions = ModelAgentPlanner(router).infer("send hello", None)
    assert observations == ("found context",)
    assert actions[0].name == "send_message"
    assert actions[0].arguments["text"] == "hello"


def test_model_planner_rejects_non_json_output():
    router = make_router("not json")
    try:
        ModelAgentPlanner(router).infer("hello", None)
    except PlannerResponseError:
        pass
    else:
        raise AssertionError("invalid planner output must be rejected")
