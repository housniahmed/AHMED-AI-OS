from uuid import uuid4

from core.agent.models import AgentAction, AgentPhase, ApprovalStatus
from core.agent.permissions import PermissionPolicy
from core.agent.runtime import ActionExecutor, AgentPlanner, AgentRuntime
from core.context.engine import ContextEngine
from core.retrieval.engine import LexicalRetriever, MetadataRetriever, SemanticRetriever, HybridRetrievalEngine
from core.retrieval.models import RetrievalCandidate


class StaticRetriever(LexicalRetriever, SemanticRetriever, MetadataRetriever):
    def search(self, query):
        return [RetrievalCandidate(uuid4(), "known context", "memory", "m1", "internal", 1.0, 1.0, 1.0)]


class Planner(AgentPlanner):
    def infer(self, request, context):
        return (("context inspected",), (AgentAction("send_message", "send a message", "execute"),))


class Executor(ActionExecutor):
    def __init__(self):
        self.calls = 0

    def execute(self, action):
        self.calls += 1
        return "ok"


def make_runtime():
    provider = StaticRetriever()
    return AgentRuntime(HybridRetrievalEngine(provider, provider, provider), ContextEngine(), Planner(), Executor())


def test_execute_action_stops_for_approval():
    runtime = make_runtime()
    state = runtime.run("send it")
    assert state.phase == AgentPhase.APPROVE
    assert state.approval == ApprovalStatus.PENDING
    assert runtime.executor.calls == 0


def test_approved_action_executes():
    runtime = make_runtime()
    state = runtime.run("send it", ApprovalStatus.APPROVED)
    assert state.phase == AgentPhase.COMPLETE
    assert state.result == ["ok"]
    assert runtime.executor.calls == 1


def test_read_action_needs_no_approval():
    policy = PermissionPolicy()
    action = AgentAction("inspect", "inspect data", "read")
    assert policy.approval_for(action) == ApprovalStatus.NOT_REQUIRED
    assert policy.can_execute(action, ApprovalStatus.NOT_REQUIRED)
