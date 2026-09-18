"""Canonical planning models.

Planning is intentionally deterministic and provider-neutral. It stores intent
and work state; it does not execute external actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class Milestone:
    title: str
    project_id: UUID
    id: UUID = field(default_factory=uuid4)
    description: str = ""
    due_at: datetime | None = None
    completed: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Task:
    title: str
    project_id: UUID
    id: UUID = field(default_factory=uuid4)
    milestone_id: UUID | None = None
    description: str = ""
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_at: datetime | None = None
    dependency_ids: tuple[UUID, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.id in self.dependency_ids:
            raise ValueError("a task cannot depend on itself")


@dataclass(frozen=True, slots=True)
class ProjectPlan:
    goal_id: UUID
    project_id: UUID
    milestone_ids: tuple[UUID, ...]
    task_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class PlanningSnapshot:
    goal_id: UUID | None
    project_id: UUID | None
    total_tasks: int
    completed_tasks: int
    actionable_task_ids: tuple[UUID, ...]
    blocked_task_ids: tuple[UUID, ...]
    overdue_task_ids: tuple[UUID, ...]
    progress: float
