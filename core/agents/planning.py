"""Agent planning and task decomposition contracts."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4
from .models import AgentRole, AgentTask, MultiAgentPlan

@dataclass(frozen=True, slots=True)
class DecompositionRequest:
    objective: str
    context: Any = None
    constraints: tuple[str, ...] = ()
    max_tasks: int = 20
    id: UUID = field(default_factory=uuid4)
    def __post_init__(self) -> None:
        if not self.objective.strip(): raise ValueError("objective cannot be empty")
        if self.max_tasks < 1: raise ValueError("max_tasks must be positive")

@dataclass(frozen=True, slots=True)
class TaskProposal:
    description: str
    role: AgentRole = AgentRole.GENERAL
    dependency_indexes: tuple[int, ...] = ()
    priority: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class DecompositionResult:
    request_id: UUID
    plan: MultiAgentPlan
    rationale: str = ""
    warnings: tuple[str, ...] = ()

class TaskDecomposer(ABC):
    @abstractmethod
    def decompose(self, request: DecompositionRequest) -> tuple[TaskProposal, ...]:
        raise NotImplementedError

class PlanValidator:
    def validate(self, request: DecompositionRequest, proposals: tuple[TaskProposal, ...]) -> None:
        if not proposals: raise ValueError("decomposer returned no tasks")
        if len(proposals) > request.max_tasks: raise ValueError("decomposition exceeds max_tasks")
        for index, proposal in enumerate(proposals):
            if not proposal.description.strip(): raise ValueError("task description cannot be empty")
            if not 1 <= proposal.priority <= 5: raise ValueError("task priority must be between 1 and 5")
            for dep in proposal.dependency_indexes:
                if dep < 0 or dep >= len(proposals) or dep == index: raise ValueError("invalid task dependency index")

class AgentPlanningEngine:
    """Turns decomposer proposals into an explicit, validated DAG."""
    def __init__(self, decomposer: TaskDecomposer, validator: PlanValidator | None = None) -> None:
        self.decomposer = decomposer
        self.validator = validator or PlanValidator()
    def create_plan(self, request: DecompositionRequest) -> DecompositionResult:
        proposals = tuple(self.decomposer.decompose(request))
        self.validator.validate(request, proposals)
        tasks: list[AgentTask] = []
        for proposal in proposals:
            deps = tuple(tasks[i].id for i in proposal.dependency_indexes)
            tasks.append(AgentTask(description=proposal.description, role=proposal.role,
                                   dependency_ids=deps, metadata={**proposal.metadata, "priority": proposal.priority}))
        plan = MultiAgentPlan(tuple(tasks), metadata={"request_id": str(request.id)})
        plan.topological_order()
        return DecompositionResult(request.id, plan)

class StaticTaskDecomposer(TaskDecomposer):
    def __init__(self, proposals: tuple[TaskProposal, ...]) -> None: self.proposals = proposals
    def decompose(self, request: DecompositionRequest) -> tuple[TaskProposal, ...]: return self.proposals
