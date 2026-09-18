"""Provider-neutral contracts for the Unified Orchestrator."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID, uuid4
from core.agent.models import AgentState, ApprovalStatus
from core.identity.models import UserContextSnapshot

class ExecutionMode(str, Enum):
    READ_ONLY = "read_only"
    PREPARE = "prepare"
    APPROVAL = "approval"
    EXECUTE = "execute"

class OrchestrationState(str, Enum):
    RECEIVED = "received"
    CONTEXT_BOUND = "context_bound"
    AGENT_COMPLETED = "agent_completed"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass(frozen=True, slots=True)
class OrchestrationRequest:
    user_id: UUID
    text: str
    execution_mode: ExecutionMode = ExecutionMode.APPROVAL
    approval: ApprovalStatus = ApprovalStatus.NOT_REQUIRED
    metadata: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("orchestration request text cannot be empty")

@dataclass(frozen=True, slots=True)
class OrchestrationResult:
    request: OrchestrationRequest
    state: OrchestrationState
    user_context: UserContextSnapshot | None
    agent_state: AgentState | None = None
    planning_snapshot: Any | None = None
    upcoming_events: tuple[Any, ...] = ()
    overdue_events: tuple[Any, ...] = ()
    memory_update: Any | None = None
    error: str | None = None
