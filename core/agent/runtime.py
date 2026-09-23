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
            user_id: UUID | None = None) -> AgentState:
        state = AgentState(request=request)
        try:
            retrieval = self.retrieval.retrieve(RetrievalQuery(text=request))
            structured = self.context.build(retrieval)
            state = state.transition(AgentPhase.INFER, context=structured)

            observations, proposals = self.planner.infer(request, structured)
            state = state.transition(AgentPhase.PROPOSE, observations=observations, proposals=proposals)

            if not proposals:
                return state.transition(AgentPhase.COMPLETE, result=None)

            for action in proposals:
                required = self.policy.approval_for(action)
                if required == ApprovalStatus.PENDING and approval != ApprovalStatus.APPROVED:
                    return state.transition(AgentPhase.APPROVE, approval=ApprovalStatus.PENDING)
                if not self.policy.can_execute(action, approval):
                    return state.transition(AgentPhase.APPROVE, approval=ApprovalStatus.REJECTED)

            results = [self.executor.execute_for_user(action, user_id) for action in proposals]
            return state.transition(AgentPhase.EXECUTE, approval=approval, result=results).transition(AgentPhase.COMPLETE)
        except Exception as exc:
            return state.transition(AgentPhase.FAILED, error=str(exc))
