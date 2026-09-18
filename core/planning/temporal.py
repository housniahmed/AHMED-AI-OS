"""Adapters between planning objects and temporal intelligence."""

from __future__ import annotations

from core.planning.models import Milestone, Task
from core.temporal.models import Event, EventType


def task_event(task: Task) -> Event | None:
    if task.due_at is None:
        return None
    return Event(
        name=f"Deadline: {task.title}",
        event_type=EventType.DEADLINE,
        start_at=task.due_at,
        entity_ids=(task.id,),
        provenance={"source_type": "planning_task", "source_id": str(task.id)},
        metadata={
            "project_id": str(task.project_id),
            "milestone_id": str(task.milestone_id) if task.milestone_id else None,
        },
    )


def milestone_event(milestone: Milestone) -> Event | None:
    if milestone.due_at is None:
        return None
    return Event(
        name=f"Milestone: {milestone.title}",
        event_type=EventType.MILESTONE,
        start_at=milestone.due_at,
        entity_ids=(milestone.id,),
        provenance={"source_type": "planning_milestone", "source_id": str(milestone.id)},
        metadata={"project_id": str(milestone.project_id), "completed": milestone.completed},
    )
