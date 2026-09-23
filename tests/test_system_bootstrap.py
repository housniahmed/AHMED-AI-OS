from core.identity.models import UserIdentity
from core.orchestration.models import OrchestrationRequest
from core.system.bootstrap import GatewayActionExecutor, SystemBootstrap
from core.conversation.service import OrchestratorConversationProvider


def test_bootstrap_shares_core_services():
    system = SystemBootstrap().build()
    assert system.orchestrator.context_provider is system.identity
    assert isinstance(system.conversations._provider, OrchestratorConversationProvider)
    assert system.gateway.security is system.security
    assert system.gateway.governance is system.governance
    assert isinstance(system.agent.executor, GatewayActionExecutor)
    assert system.agent.executor.gateway is system.gateway


def test_provider_free_stack_is_explicit_and_does_not_execute_tools():
    system = SystemBootstrap().build()
    user_id = __import__("uuid").uuid4()
    system.identity.create(UserIdentity(user_id=user_id, display_name="Bootstrap Test"))

    result = system.orchestrator.run(
        OrchestrationRequest(user_id=user_id, text="Hello")
    )

    assert result.state.value == "completed"
    assert result.agent_state is not None
    assert result.agent_state.proposals == ()
