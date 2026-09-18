from uuid import uuid4
from core.agent.models import AgentAction, ApprovalStatus
from core.domain.models import ActionLevel
from core.tools.gateway import GatewayRequest, ToolExecutionGateway
from core.tools.models import ToolSpec
from core.tools.registry import ToolRegistry
from core.tools.runtime import ToolRuntime
from core.tools.permissions import ToolPermissionPolicy

def make_gateway(level=ActionLevel.EXECUTE, allowed=True):
    registry = ToolRegistry()
    registry.register(ToolSpec("send", "send", level))
    runtime = ToolRuntime(registry, ToolPermissionPolicy({"send"} if allowed else set()))
    runtime.bind("send", lambda args: {"ok": args.get("value")})
    return ToolExecutionGateway(runtime)

def test_prepare_action_can_call_prepare_tool():
    result = make_gateway(ActionLevel.PREPARE).execute(
        GatewayRequest(AgentAction("send", "prepare", "prepare", {"value": 1}), uuid4()))
    assert result.result.success
    assert result.result.output == {"ok": 1}

def test_execute_tool_requires_explicit_approval():
    gateway = make_gateway()
    action = AgentAction("send", "execute", "execute", {"value": 2})
    denied = gateway.execute(GatewayRequest(action, uuid4()))
    approved = gateway.execute(GatewayRequest(action, uuid4(), ApprovalStatus.APPROVED))
    assert not denied.result.success
    assert approved.result.success

def test_action_cannot_escalate_tool_level():
    result = make_gateway(ActionLevel.PREPARE).execute(
        GatewayRequest(AgentAction("send", "execute", "execute", {"value": 3}), uuid4(), ApprovalStatus.APPROVED))
    assert not result.result.success
    assert "does not permit" in result.result.error

def test_unknown_tool_is_rejected():
    registry = ToolRegistry()
    runtime = ToolRuntime(registry, ToolPermissionPolicy({"missing"}))
    result = ToolExecutionGateway(runtime).execute(
        GatewayRequest(AgentAction("missing", "x"), uuid4()))
    assert not result.result.success
    assert result.tool_call is None

def test_batch_preserves_order():
    gateway = make_gateway()
    requests = tuple(GatewayRequest(AgentAction("send", str(i), "prepare", {"value": i}), uuid4()) for i in range(3))
    results = gateway.execute_many(requests)
    assert [r.result.output for r in results] == [{"ok": 0}, {"ok": 1}, {"ok": 2}]
