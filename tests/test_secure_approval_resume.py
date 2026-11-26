from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import pytest
from core.agent.models import AgentAction, AgentPhase
from core.governance.models import ApprovalDecision
from core.domain.models import ActionLevel
from core.security.models import AccessLevel
from core.system.bootstrap import SystemBootstrap
from core.tools.models import ToolSpec
from core.tools.permissions import ToolPermissionPolicy

def setup():
    system = SystemBootstrap().build()
    user = uuid4()
    calls = []
    system.tool_registry.register(ToolSpec("send", "send", ActionLevel.EXECUTE))
    system.tool_runtime.policy = ToolPermissionPolicy({"send"})
    system.tool_runtime.bind("send", lambda args: calls.append(args) or args)
    system.security.grant(user, "send", AccessLevel.EXECUTE)
    return system, user, calls

def test_resume_without_replanning_and_replay():
    system, user, calls = setup()
    args = {"nested": {"value": 7}}
    class Planner:
        count = 0
        def infer(self, request, context):
            self.count += 1
            return (), (AgentAction("send", "send", "execute", args),)
    planner = Planner()
    system.agent.planner = planner
    state = system.agent.run("send", user_id=user)
    assert state.phase is AgentPhase.APPROVE
    from uuid import UUID
    request_id = UUID(state.result["approval_request_id"])
    assert not calls
    assert not system.gateway.resume(request_id, user).result.success
    with pytest.raises(PermissionError):
        system.gateway.resume(request_id, uuid4())
    args["nested"]["value"] = 99
    system.governance.decide(request_id, ApprovalDecision.APPROVED, user)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: system.gateway.resume(request_id, user), range(2)))
    assert sum(r.result.success for r in results) == 1
    assert calls == [{"nested": {"value": 7}}]
    assert planner.count == 1

def test_revoked_permission_blocks_resume():
    system, user, calls = setup()
    request_id = system.agent.executor.prepare_approval(AgentAction("send","send","execute",{}), user)
    system.governance.decide(request_id, ApprovalDecision.APPROVED, user)
    system.security.revoke(user, "send")
    assert not system.gateway.resume(request_id, user).result.success
    assert not calls
