"""Controlled execution boundary with Security and Governance integration."""
from __future__ import annotations
from dataclasses import dataclass, field
from uuid import UUID, uuid4
from core.agent.models import AgentAction, ApprovalStatus
from core.domain.models import ActionLevel
from core.tools.models import ToolCall, ToolResult
from core.tools.runtime import ToolRuntime
from core.security.models import AccessLevel, SecurityAction, SecurityPrincipal
from core.security.service import SecurityService
from core.governance.models import ApprovalDecision, ApprovalRequest, GovernanceAction, RiskLevel
from core.governance.service import GovernanceService

@dataclass(frozen=True, slots=True)
class GatewayRequest:
    action: AgentAction
    user_id: UUID
    approval: ApprovalStatus = ApprovalStatus.NOT_REQUIRED
    governance_request_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)

@dataclass(frozen=True, slots=True)
class GatewayResult:
    request_id: UUID
    tool_call: ToolCall | None
    result: ToolResult
    governance_request_id: UUID | None = None

class ToolExecutionGateway:
    """Single execution boundary; optional B33 Security and B18 Governance are enforced here."""
    def __init__(self, runtime: ToolRuntime, security: SecurityService | None = None,
                 governance: GovernanceService | None = None) -> None:
        self.runtime=runtime; self.security=security; self.governance=governance

    def execute(self, request: GatewayRequest) -> GatewayResult:
        action=request.action
        try:
            spec=self.runtime.registry.get(action.name)
            if not self._level_allowed(action.level,spec.action_level):
                return self._failure(request,f"action level does not permit tool level: {action.level} -> {spec.action_level.value}")
            if self.security is not None:
                required=AccessLevel.EXECUTE if ActionLevel(action.level) is ActionLevel.EXECUTE else AccessLevel.WRITE if ActionLevel(action.level) in {ActionLevel.PREPARE,ActionLevel.APPROVE} else AccessLevel.READ
                decision=self.security.authorize(SecurityPrincipal(request.user_id),SecurityAction(spec.name,"execute",required))
                if not decision.allowed: return self._failure(request,decision.reason)
            governance_id=request.governance_request_id
            if self.governance is not None and ActionLevel(action.level) in {ActionLevel.APPROVE,ActionLevel.EXECUTE}:
                if governance_id is None:
                    pending=self.governance.request(ApprovalRequest(GovernanceAction(action.name,spec.name,RiskLevel.HIGH,dict(action.arguments)),request.user_id))
                    return self._failure(request,"human approval required",pending.request_id)
                if not self.governance.can_execute(governance_id):
                    return self._failure(request,"governance approval not granted",governance_id)
            call=ToolCall(tool_name=spec.name,arguments=dict(action.arguments))
            result=self.runtime.execute(call,approved=request.approval==ApprovalStatus.APPROVED)
            return GatewayResult(request.id,call,result,governance_id)
        except Exception as exc:
            return self._failure(request,str(exc),request.governance_request_id)

    def execute_many(self,requests:tuple[GatewayRequest,...])->tuple[GatewayResult,...]:
        return tuple(self.execute(r) for r in requests)

    @staticmethod
    def _level_allowed(action_level:str,tool_level:ActionLevel)->bool:
        try: requested=ActionLevel(action_level)
        except ValueError: return False
        rank={ActionLevel.READ:0,ActionLevel.ANALYZE:1,ActionLevel.PREPARE:2,ActionLevel.APPROVE:3,ActionLevel.EXECUTE:4}
        return rank[requested] <= rank[tool_level]

    @staticmethod
    def _failure(request:GatewayRequest,error:str,governance_request_id:UUID|None=None)->GatewayResult:
        return GatewayResult(request.id,None,ToolResult(request.action.name,False,error=error),governance_request_id)
