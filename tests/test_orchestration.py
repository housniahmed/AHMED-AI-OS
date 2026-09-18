from uuid import uuid4
from core.agent.models import AgentPhase, AgentState, ApprovalStatus
from core.identity.models import UserIdentity
from core.identity.service import UserContextService
from core.orchestration.models import ExecutionMode, OrchestrationRequest, OrchestrationState
from core.orchestration.orchestrator import UnifiedOrchestrator

class StubAgentRuntime:
    def __init__(self, state): self.state, self.calls = state, []
    def run(self, request, approval=ApprovalStatus.NOT_REQUIRED):
        self.calls.append((request, approval)); return self.state

class StubPlanning:
    def snapshot(self, project_id=None, goal_id=None, now=None): return {"project_id": project_id, "goal_id": goal_id}

class StubTemporal:
    def upcoming(self, now=None, limit=10): return ("upcoming",)
    def overdue(self, now=None): return ("overdue",)

def make_service():
    service = UserContextService()
    identity = UserIdentity(user_id=uuid4(), display_name="Ahmed", timezone="Africa/Casablanca")
    service.create(identity)
    return service, identity

def test_orchestrator_binds_identity_and_delegates():
    service, identity = make_service()
    agent = StubAgentRuntime(AgentState(request="hello", phase=AgentPhase.COMPLETE))
    orchestrator = UnifiedOrchestrator(service, agent, planning=StubPlanning(), temporal=StubTemporal())
    result = orchestrator.run(OrchestrationRequest(identity.user_id, "hello"))
    assert result.state == OrchestrationState.COMPLETED
    assert result.user_context.identity.user_id == identity.user_id
    assert agent.calls == [("hello", ApprovalStatus.NOT_REQUIRED)]
    assert result.upcoming_events == ("upcoming",)
    assert result.overdue_events == ("overdue",)

def test_prepare_mode_does_not_forward_approval():
    service, identity = make_service()
    agent = StubAgentRuntime(AgentState(request="send", phase=AgentPhase.APPROVE, approval=ApprovalStatus.PENDING))
    orchestrator = UnifiedOrchestrator(service, agent)
    result = orchestrator.run(OrchestrationRequest(identity.user_id, "send", execution_mode=ExecutionMode.PREPARE,
                                                    approval=ApprovalStatus.APPROVED))
    assert result.state == OrchestrationState.WAITING_APPROVAL
    assert agent.calls == [("send", ApprovalStatus.NOT_REQUIRED)]

def test_unknown_user_fails_without_fabricating_context():
    service = UserContextService()
    agent = StubAgentRuntime(AgentState(request="hello", phase=AgentPhase.COMPLETE))
    result = UnifiedOrchestrator(service, agent).run(OrchestrationRequest(uuid4(), "hello"))
    assert result.state == OrchestrationState.FAILED
    assert result.user_context is None
