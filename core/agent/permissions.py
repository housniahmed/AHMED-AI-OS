"""Policy gate separating planning from real-world execution."""

from __future__ import annotations

from core.domain.models import ActionLevel
from core.agent.models import AgentAction, ApprovalStatus


class PermissionPolicy:
    """Deterministic default policy for human-in-the-loop execution."""

    def __init__(self, execution_requires_approval: bool = True) -> None:
        self.execution_requires_approval = execution_requires_approval

    def approval_for(self, action: AgentAction) -> ApprovalStatus:
        level = ActionLevel(action.level)
        if level in {ActionLevel.READ, ActionLevel.ANALYZE, ActionLevel.PREPARE}:
            return ApprovalStatus.NOT_REQUIRED
        if level == ActionLevel.APPROVE:
            return ApprovalStatus.PENDING
        if level == ActionLevel.EXECUTE and self.execution_requires_approval:
            return ApprovalStatus.PENDING
        return ApprovalStatus.NOT_REQUIRED

    def can_execute(self, action: AgentAction, approval: ApprovalStatus) -> bool:
        required = self.approval_for(action)
        return required != ApprovalStatus.PENDING or approval == ApprovalStatus.APPROVED
