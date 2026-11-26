from uuid import uuid4
from core.agent.models import AgentAction, ApprovalStatus
from core.governance.models import ApprovalDecision
from core.governance.service import GovernanceService
from core.security.models import AccessLevel
from core.security.service import SecurityService
from core.tools.gateway import GatewayRequest, ToolExecutionGateway
from core.tools.models import ToolSpec
from core.tools.registry import ToolRegistry
from core.tools.runtime import ToolRuntime
from core.tools.permissions import ToolPermissionPolicy
from core.domain.models import ActionLevel

def make():
    registry=ToolRegistry()
    registry.register(ToolSpec("send","send",ActionLevel.EXECUTE))
    runtime=ToolRuntime(registry,ToolPermissionPolicy({"send"}))
    runtime.bind("send",lambda args: {"ok":args["value"]})
    security=SecurityService()
    governance=GovernanceService()
    user=uuid4()
    security.grant(user,"send",AccessLevel.EXECUTE)
    return ToolExecutionGateway(runtime,security,governance),governance,user

def test_gateway_requires_security_and_governance():
    gateway,governance,user=make()
    action=AgentAction("send","send","execute",{"value":7})
    pending=gateway.execute(GatewayRequest(action,user))
    assert not pending.result.success
    assert pending.governance_request_id is not None
    assert not gateway.execute(GatewayRequest(action,user,governance_request_id=pending.governance_request_id)).result.success
    governance.decide(pending.governance_request_id,ApprovalDecision.APPROVED,user)
    assert not gateway.execute(GatewayRequest(action,user,governance_request_id=pending.governance_request_id)).result.success
    approved=gateway.execute(GatewayRequest(action,user,ApprovalStatus.APPROVED,governance_request_id=pending.governance_request_id))
    assert approved.result.success
    assert approved.result.output=={"ok":7}

def test_gateway_denies_without_security():
    gateway,governance,user=make()
    other=uuid4()
    action=AgentAction("send","send","execute",{"value":1})
    result=gateway.execute(GatewayRequest(action,other))
    assert not result.result.success
    assert "permission" in result.result.error


def test_governance_approval_cannot_authorize_changed_arguments():
    gateway,governance,user=make()
    action=AgentAction("send","send","execute",{"value":7})
    pending=gateway.execute(GatewayRequest(action,user))
    governance.decide(pending.governance_request_id,ApprovalDecision.APPROVED,user)
    changed=AgentAction("send","send","execute",{"value":8})
    result=gateway.execute(GatewayRequest(changed,user,ApprovalStatus.APPROVED,governance_request_id=pending.governance_request_id))
    assert not result.result.success
    assert "does not match" in result.result.error
