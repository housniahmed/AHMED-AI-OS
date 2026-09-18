"""Provider-neutral workflow domain models."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

class WorkflowState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class StepState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass(frozen=True, slots=True)
class WorkflowStep:
    name: str
    id: UUID = field(default_factory=uuid4)
    dependency_ids: tuple[UUID, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    def __post_init__(self) -> None:
        if not self.name.strip(): raise ValueError("workflow step name cannot be empty")
        if self.id in self.dependency_ids: raise ValueError("workflow step cannot depend on itself")

@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    name: str
    steps: tuple[WorkflowStep, ...]
    id: UUID = field(default_factory=uuid4)
    metadata: dict[str, Any] = field(default_factory=dict)
    def __post_init__(self) -> None:
        if not self.name.strip(): raise ValueError("workflow name cannot be empty")
        ids = {s.id for s in self.steps}
        if len(ids) != len(self.steps): raise ValueError("workflow step ids must be unique")
        for step in self.steps:
            if set(step.dependency_ids) - ids: raise ValueError("workflow step has unknown dependency")
        self.topological_order()
    def topological_order(self) -> tuple[WorkflowStep, ...]:
        remaining = {s.id: s for s in self.steps}
        done = set()
        ordered = []
        while remaining:
            ready = [s for s in remaining.values() if set(s.dependency_ids) <= done]
            if not ready: raise ValueError("workflow contains a dependency cycle")
            ready.sort(key=lambda s: str(s.id))
            for step in ready:
                ordered.append(step); done.add(step.id); del remaining[step.id]
        return tuple(ordered)

@dataclass(frozen=True, slots=True)
class StepResult:
    step_id: UUID
    state: StepState
    output: Any = None
    error: str | None = None

@dataclass(frozen=True, slots=True)
class WorkflowRun:
    workflow_id: UUID
    id: UUID = field(default_factory=uuid4)
    state: WorkflowState = WorkflowState.PENDING
    input_data: Any = None
    step_states: dict[UUID, StepState] = field(default_factory=dict)
    outputs: dict[UUID, Any] = field(default_factory=dict)
    errors: dict[UUID, str] = field(default_factory=dict)
    current_step_id: UUID | None = None
    checkpoint: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
