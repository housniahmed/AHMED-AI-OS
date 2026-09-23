"""Top-level, provider-neutral coordinator for AHMED AI OS."""
from __future__ import annotations
from typing import Any, Protocol
from uuid import UUID
from core.agent.models import ApprovalStatus
from core.agent.runtime import AgentRuntime
from core.identity.models import UserContextSnapshot
from core.orchestration.models import ExecutionMode, OrchestrationRequest, OrchestrationResult, OrchestrationState

class ContextProvider(Protocol):
    def snapshot(self, user_id: UUID) -> UserContextSnapshot: ...

class PlanningProvider(Protocol):
    def snapshot(self, project_id=None, goal_id=None, now=None): ...

class TemporalProvider(Protocol):
    def upcoming(self, now=None, limit: int = 10): ...
    def overdue(self, now=None): ...

class MemoryUpdateSink(Protocol):
    def update(self, request: OrchestrationRequest, result: OrchestrationResult) -> Any: ...

class UnifiedOrchestrator:
    """Coordinate identity, context, planning, temporal intelligence and agent execution."""
    def __init__(self, context_provider: ContextProvider, agent_runtime: AgentRuntime,
                 planning: PlanningProvider | None = None, temporal: TemporalProvider | None = None,
                 memory_updates: MemoryUpdateSink | None = None) -> None:
        self.context_provider = context_provider
        self.agent_runtime = agent_runtime
        self.planning = planning
        self.temporal = temporal
        self.memory_updates = memory_updates

    def run(self, request: OrchestrationRequest) -> OrchestrationResult:
        try:
            context = self.context_provider.snapshot(request.user_id)
            if context.identity.user_id != request.user_id:
                raise ValueError("context provider returned a different user identity")
            planning_snapshot = self._planning_snapshot(context)
            upcoming, overdue = self._temporal_snapshot()
            agent_state = self.agent_runtime.run(
                request.text,
                approval=self._effective_approval(request),
                user_id=request.user_id,
            )
            if agent_state.phase.value == "approve":
                state = OrchestrationState.WAITING_APPROVAL
            elif agent_state.phase.value == "complete":
                state = OrchestrationState.COMPLETED
            elif agent_state.phase.value == "failed":
                state = OrchestrationState.FAILED
            else:
                state = OrchestrationState.AGENT_COMPLETED
            result = OrchestrationResult(request, state, context, agent_state,
                                         planning_snapshot, tuple(upcoming), tuple(overdue))
            if self.memory_updates is not None and state == OrchestrationState.COMPLETED:
                update = self.memory_updates.update(request, result)
                result = OrchestrationResult(request, state, context, agent_state,
                                             planning_snapshot, tuple(upcoming), tuple(overdue), update)
            return result
        except Exception as exc:
            context = None
            try:
                context = self.context_provider.snapshot(request.user_id)
            except Exception:
                pass
            return OrchestrationResult(request, OrchestrationState.FAILED, context, error=str(exc))

    def _planning_snapshot(self, context: UserContextSnapshot):
        if self.planning is None:
            return None
        if len(context.active_project_ids) == 1:
            return self.planning.snapshot(project_id=context.active_project_ids[0])
        if len(context.active_goal_ids) == 1:
            return self.planning.snapshot(goal_id=context.active_goal_ids[0])
        return self.planning.snapshot()

    def _temporal_snapshot(self):
        if self.temporal is None:
            return (), ()
        return self.temporal.upcoming(), self.temporal.overdue()

    @staticmethod
    def _effective_approval(request: OrchestrationRequest) -> ApprovalStatus:
        if request.execution_mode in {ExecutionMode.READ_ONLY, ExecutionMode.PREPARE}:
            return ApprovalStatus.NOT_REQUIRED
        return request.approval
