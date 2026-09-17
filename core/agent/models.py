"""Explicit state and action contracts for the agent runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class AgentPhase(str, Enum):
    KNOW = "know"
    INFER = "infer"
    PROPOSE = "propose"
    APPROVE = "approve"
    EXECUTE = "execute"
    COMPLETE = "complete"
    FAILED = "failed"


class ApprovalStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class AgentAction:
    name: str
    description: str
    level: str = "prepare"
    arguments: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True)
class AgentState:
    request: str
    phase: AgentPhase = AgentPhase.KNOW
    context: Any | None = None
    observations: tuple[str, ...] = ()
    proposals: tuple[AgentAction, ...] = ()
    approval: ApprovalStatus = ApprovalStatus.NOT_REQUIRED
    result: Any | None = None
    error: str | None = None

    def transition(self, phase: AgentPhase, **changes: Any) -> "AgentState":
        return AgentState(
            request=self.request,
            phase=phase,
            context=changes.get("context", self.context),
            observations=changes.get("observations", self.observations),
            proposals=changes.get("proposals", self.proposals),
            approval=changes.get("approval", self.approval),
            result=changes.get("result", self.result),
            error=changes.get("error", self.error),
        )
