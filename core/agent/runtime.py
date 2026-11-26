"""Provider-agnostic orchestration state machine for AHMED AI OS."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from core.agent.models import AgentAction, AgentPhase, AgentState, ApprovalStatus
from core.agent.permissions import PermissionPolicy
from core.context.engine import ContextEngine
from core.retrieval.engine import HybridRetrievalEngine
from core.retrieval.models import RetrievalQuery


class ActionExecutor(ABC):
    @abstractmethod
    def execute(self, action: AgentAction) -> Any:
        raise NotImplementedError

    def prepare_approval(self, action: AgentAction, user_id: UUID | None = None) -> UUID | None:
        return None

    def execute_for_user(self, action: AgentAction, user_id: UUID | None = None) -> Any:
        """Optional request-scoped execution hook; legacy executors remain valid."""
        return self.execute(action)


class AgentPlanner(ABC):
    @abstractmethod
    def infer(self, request: str, context: Any) -> tuple[tuple[str, ...], tuple[AgentAction, ...]]:
        raise NotImplementedError


class AgentRuntime:
    """Run KNOW -> INFER -> PROPOSE and execute only after policy approval."""

    def __init__(self, retrieval: HybridRetrievalEngine, context: ContextEngine,
                 planner: AgentPlanner, executor: ActionExecutor,
                 policy: PermissionPolicy | None = None) -> None:
        self.retrieval = retrieval
        self.context = context
        self.planner = planner
        self.executor = executor
        self.policy = policy or PermissionPolicy()

    def run(self, request: str, approval: ApprovalStatus = ApprovalStatus.NOT_REQUIRED,
            user_id: UUID | None = None, conversation_history=()) -> AgentState:
        state = AgentState(request=request)
        try:
            retrieval = self.retrieval.retrieve(RetrievalQuery(text=request, user_id=user_id))
            structured = self.context.build(retrieval)
            if conversation_history:
                from dataclasses import replace
                structured = replace(structured, conversation_history=conversation_history)
            state = state.transition(AgentPhase.INFER, context=structured)

            observations, proposals = self.planner.infer(request, structured)
            state = state.transition(AgentPhase.PROPOSE, observations=observations, proposals=proposals)

            if conversation_history and proposals:
                return state.transition(AgentPhase.FAILED, error='History-assisted requests cannot execute or prepare tools; submit a fresh standalone request')

            if not proposals:
                return state.transition(AgentPhase.COMPLETE, result=None)

            # Never execute a partial mixed batch while waiting for approval.
            if any(self.policy.approval_for(a) == ApprovalStatus.PENDING for a in proposals):
                if hasattr(self.executor, "gateway"):
                    if len(proposals) != 1:
                        return state.transition(AgentPhase.FAILED, error="Approval requires a single action; split the request")
                    request_id = self.executor.prepare_approval(proposals[0], user_id)
                    if request_id is None:
                        return state.transition(AgentPhase.FAILED, error="Unable to prepare authorized approval")
                    return state.transition(AgentPhase.APPROVE, approval=ApprovalStatus.PENDING, result={"approval_request_id": str(request_id)})

            for action in proposals:
                required = self.policy.approval_for(action)
                if required == ApprovalStatus.PENDING and approval != ApprovalStatus.APPROVED:
                    return state.transition(AgentPhase.APPROVE, approval=ApprovalStatus.PENDING)
                if not self.policy.can_execute(action, approval):
                    return state.transition(AgentPhase.APPROVE, approval=ApprovalStatus.REJECTED)

            results = [self.executor.execute_for_user(action, user_id) for action in proposals]
            from core.tools.models import ToolResult
            if any(isinstance(result, ToolResult) and not result.success for result in results):
                return state.transition(AgentPhase.FAILED, result=results, error='Tool execution denied or failed')
            return state.transition(AgentPhase.EXECUTE, approval=approval, result=results).transition(AgentPhase.COMPLETE)
        except Exception as exc:
            return state.transition(AgentPhase.FAILED, error=str(exc))
