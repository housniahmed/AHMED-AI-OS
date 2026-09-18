from datetime import datetime, timezone, timedelta

import pytest

from core.domain.models import Goal, Project
from core.planning.engine import PlanningEngine
from core.planning.models import Milestone, Task, TaskPriority, TaskStatus
from core.planning.temporal import task_event
from core.temporal.models import EventType


def setup_engine():
    engine = PlanningEngine()
    goal = engine.add_goal(Goal("Ship research paper"))
    project = engine.add_project(Project("Paper project", goal_ids=[goal.id]))
    return engine, goal, project


def test_dependencies_and_actionable_tasks():
    engine, _, project = setup_engine()
    first = engine.add_task(Task("Prepare dataset", project.id, priority=TaskPriority.HIGH))
    second = engine.add_task(Task("Run analysis", project.id, dependency_ids=(first.id,)))
    assert tuple(t.id for t in engine.actionable_tasks(project.id)) == (first.id,)
    with pytest.raises(ValueError, match="dependencies"):
        engine.update_task_status(second.id, TaskStatus.IN_PROGRESS)
    engine.update_task_status(first.id, TaskStatus.COMPLETED)
    assert tuple(t.id for t in engine.actionable_tasks(project.id)) == (second.id,)


def test_cross_project_dependency_is_rejected():
    engine, goal, project = setup_engine()
    other = engine.add_project(Project("Other project", goal_ids=[goal.id]))
    first = engine.add_task(Task("First", project.id))
    with pytest.raises(ValueError, match="same project"):
        engine.add_task(Task("Second", other.id, dependency_ids=(first.id,)))


def test_dependency_cycle_is_rejected():
    engine, _, project = setup_engine()
    a = engine.add_task(Task("A", project.id))
    b = engine.add_task(Task("B", project.id, dependency_ids=(a.id,)))
    with pytest.raises(ValueError, match="cycle"):
        engine.add_dependency(a.id, b.id)


def test_progress_and_overdue():
    engine, _, project = setup_engine()
    now = datetime(2026, 9, 18, tzinfo=timezone.utc)
    old = engine.add_task(Task("Old", project.id, due_at=now - timedelta(days=1)))
    new = engine.add_task(Task("New", project.id, due_at=now + timedelta(days=1)))
    engine.update_task_status(old.id, TaskStatus.COMPLETED)
    snapshot = engine.snapshot(project.id, now=now)
    assert snapshot.total_tasks == 2
    assert snapshot.completed_tasks == 1
    assert snapshot.progress == 0.5
    assert snapshot.overdue_task_ids == ()
    assert snapshot.actionable_task_ids == (new.id,)


def test_milestone_and_deadline_event():
    engine, _, project = setup_engine()
    due = datetime(2026, 9, 20, tzinfo=timezone.utc)
    milestone = engine.add_milestone(Milestone("Submission", project.id, due_at=due))
    task = engine.add_task(Task("Submit", project.id, milestone_id=milestone.id, due_at=due))
    event = task_event(task)
    assert event is not None
    assert event.event_type == EventType.DEADLINE
    assert event.start_at == due
    assert event.entity_ids == (task.id,)
