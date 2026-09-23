from core.identity.models import UserIdentity
from core.models.contracts import ModelTask
from core.models.providers import StaticModelProvider
from core.models.router import ModelRoute, ModelRouter
from core.orchestration.models import OrchestrationRequest
from core.system.bootstrap import GatewayActionExecutor, NoOpPlanner, SystemBootstrap
from core.conversation.service import OrchestratorConversationProvider


def test_bootstrap_shares_core_services():
    system = SystemBootstrap().build()
    assert system.orchestrator.context_provider is system.identity
    assert isinstance(system.conversations._provider, OrchestratorConversationProvider)
    assert system.gateway.security is system.security
    assert system.gateway.governance is system.governance
    assert isinstance(system.agent.executor, GatewayActionExecutor)
    assert system.agent.executor.gateway is system.gateway
    assert isinstance(system.agent.planner, NoOpPlanner)


def test_provider_free_stack_is_explicit_and_does_not_execute_tools():
    system = SystemBootstrap().build()
    user_id = __import__("uuid").uuid4()
    system.identity.create(UserIdentity(user_id=user_id, display_name="Bootstrap Test"))

    result = system.orchestrator.run(OrchestrationRequest(user_id=user_id, text="Hello"))

    assert result.state.value == "completed"
    assert result.agent_state is not None
    assert result.agent_state.proposals == ()


def test_model_router_can_activate_model_backed_planner():
    provider = StaticModelProvider(
        "test-model",
        '{"observations":["model inspected context"],"actions":[]}',
    )
    router = ModelRouter(
        {"test-model": provider},
        (ModelRoute(ModelTask.REASONING, "test-model", "reasoning-test"),),
    )
    system = SystemBootstrap(model_router=router).build()
    assert system.model_router is router
    assert system.agent.planner.__class__.__name__ == "ModelAgentPlanner"

    user_id = __import__("uuid").uuid4()
    system.identity.create(UserIdentity(user_id=user_id, display_name="Model Test"))
    result = system.orchestrator.run(OrchestrationRequest(user_id=user_id, text="Hello"))
    assert result.state.value == "completed"
    assert provider.calls == 1
