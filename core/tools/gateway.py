"""Controlled gateway between agent proposals and tool execution."""
from __future__ import annotations
from dataclasses import dataclass, field
from uuid import UUID, uuid4
from core.agent.models import AgentAction, ApprovalStatus
from core.domain.models import ActionLevel
from core.tools.models import ToolCall, ToolResult
from core.tools.runtime import ToolRuntime

@dataclass(frozen=True, slots=True)
class GatewayRequest:
    action: AgentAction
    user_id: UUID
    approval: ApprovalStatus = ApprovalStatus.NOT_REQUIRED
    id: UUID = field(default_factory=uuid4)

@dataclass(frozen=True, slots=True)
class GatewayResult:
    request_id: UUID
    tool_call: ToolCall | None
    result: ToolResult

class ToolExecutionGateway:
    """Single execution boundary for converting approved agent actions into tool calls."""
    def __init__(self, runtime: ToolRuntime) -> None:
        self.runtime = runtime

    def execute(self, request: GatewayRequest) -> GatewayResult:
        action = request.action
        try:
            spec = self.runtime.registry.get(action.name)
            if not self._level_allowed(action.level, spec.action_level):
                return self._failure(request, f"action level does not permit tool level: {action.level} -> {spec.action_level.value}")
            call = ToolCall(tool_name=spec.name, arguments=dict(action.arguments))
            result = self.runtime.execute(call, approved=request.approval == ApprovalStatus.APPROVED)
            return GatewayResult(request.id, call, result)
        except Exception as exc:
            return self._failure(request, str(exc))

    def execute_many(self, requests: tuple[GatewayRequest, ...]) -> tuple[GatewayResult, ...]:
        return tuple(self.execute(request) for request in requests)

    @staticmethod
    def _level_allowed(action_level: str, tool_level: ActionLevel) -> bool:
        try:
            requested = ActionLevel(action_level)
        except ValueError:
            return False
        rank = {ActionLevel.READ: 0, ActionLevel.ANALYZE: 1, ActionLevel.PREPARE: 2,
                ActionLevel.APPROVE: 3, ActionLevel.EXECUTE: 4}
        return rank[requested] <= rank[tool_level]

    @staticmethod
    def _failure(request: GatewayRequest, error: str) -> GatewayResult:
        return GatewayResult(request.id, None, ToolResult(request.action.name, False, error=error))
