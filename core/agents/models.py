"""Provider-neutral multi-agent domain contracts."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

class AgentRole(str, Enum):
    RESEARCH = "research"
    ANALYST = "analyst"
    PLANNER = "planner"
    EXECUTOR = "executor"
    REVIEWER = "reviewer"
    GENERAL = "general"

class AgentExecutionState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"

@dataclass(frozen=True, slots=True)
class AgentTask:
    description: str
    role: AgentRole = AgentRole.GENERAL
    id: UUID = field(default_factory=uuid4)
    dependency_ids: tuple[UUID, ...] = ()
    input_data: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class AgentResult:
    task_id: UUID
    state: AgentExecutionState
    output: Any = None
    observations: tuple[str, ...] = ()
    error: str | None = None
    provenance: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class MultiAgentPlan:
    tasks: tuple[AgentTask, ...]
    id: UUID = field(default_factory=uuid4)
    metadata: dict[str, Any] = field(default_factory=dict)
    def __post_init__(self) -> None:
        ids = [task.id for task in self.tasks]
        if len(ids) != len(set(ids)):
            raise ValueError("agent task ids must be unique")
        known = set(ids)
        for task in self.tasks:
            if set(task.dependency_ids) - known:
                raise ValueError("agent task contains an unknown dependency")
            if task.id in task.dependency_ids:
                raise ValueError("agent task cannot depend on itself")
    def topological_order(self) -> tuple[AgentTask, ...]:
        remaining = {task.id: task for task in self.tasks}
        ordered = []
        completed = set()
        while remaining:
            ready = [t for t in remaining.values() if set(t.dependency_ids) <= completed]
            if not ready:
                raise ValueError("agent plan contains a dependency cycle")
            ready.sort(key=lambda t: str(t.id))
            for task in ready:
                ordered.append(task); completed.add(task.id); del remaining[task.id]
        return tuple(ordered)
