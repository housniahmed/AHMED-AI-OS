"""Deterministic Goal / Project / Task management engine."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from core.domain.models import Goal, Project
from core.planning.models import Milestone, PlanningSnapshot, ProjectPlan, Task, TaskStatus


class PlanningEngine:
    """In-memory planning aggregate with explicit state transitions.

    The engine is deliberately non-autonomous: it identifies actionable work
    and produces planning information, but never executes external actions.
    """

    def __init__(self) -> None:
        self._goals: dict[UUID, Goal] = {}
        self._projects: dict[UUID, Project] = {}
        self._milestones: dict[UUID, Milestone] = {}
        self._tasks: dict[UUID, Task] = {}

    def add_goal(self, goal: Goal) -> Goal:
        if goal.id in self._goals:
            raise ValueError(f"goal already exists: {goal.id}")
        self._goals[goal.id] = goal
        return goal

    def add_project(self, project: Project) -> Project:
        if project.id in self._projects:
            raise ValueError(f"project already exists: {project.id}")
        if not project.goal_ids:
            raise ValueError("project must reference at least one goal")
        for goal_id in project.goal_ids:
            if goal_id not in self._goals:
                raise ValueError(f"unknown goal: {goal_id}")
        self._projects[project.id] = project
        return project

    def add_milestone(self, milestone: Milestone) -> Milestone:
        if milestone.id in self._milestones:
            raise ValueError(f"milestone already exists: {milestone.id}")
        self._require_project(milestone.project_id)
        self._milestones[milestone.id] = milestone
        return milestone

    def add_task(self, task: Task) -> Task:
        if task.id in self._tasks:
            raise ValueError(f"task already exists: {task.id}")
        self._validate_task_references(task)
        self._tasks[task.id] = task
        try:
            self._assert_acyclic(task.project_id)
        except Exception:
            del self._tasks[task.id]
            raise
        return task

    def add_dependency(self, task_id: UUID, dependency_id: UUID) -> Task:
        task = self._tasks[task_id]
        dependency = self._tasks.get(dependency_id)
        if dependency is None:
            raise ValueError(f"unknown task dependency: {dependency_id}")
        if task.project_id != dependency.project_id:
            raise ValueError("task dependencies must belong to the same project")
        if task_id == dependency_id:
            raise ValueError("a task cannot depend on itself")
        if dependency_id in task.dependency_ids:
            return task
        updated = self._replace_task(task, dependency_ids=task.dependency_ids + (dependency_id,))
        self._tasks[task_id] = updated
        try:
            self._assert_acyclic(task.project_id)
        except Exception:
            self._tasks[task_id] = task
            raise
        return updated

    def update_task_status(self, task_id: UUID, status: TaskStatus) -> Task:
        task = self._tasks[task_id]
        if status == TaskStatus.IN_PROGRESS and not self.is_actionable(task_id):
            raise ValueError("task cannot start while dependencies are incomplete")
        if task.status == TaskStatus.CANCELLED and status != TaskStatus.CANCELLED:
            raise ValueError("cancelled tasks cannot be reopened by this operation")
        updated = self._replace_task(task, status=status)
        self._tasks[task_id] = updated
        return updated

    def plan_for_project(self, project_id: UUID) -> ProjectPlan:
        project = self._require_project(project_id)
        milestone_ids = tuple(m.id for m in self._milestones.values() if m.project_id == project_id)
        task_ids = tuple(t.id for t in self._tasks.values() if t.project_id == project_id)
        if not project.goal_ids:
            raise ValueError("project must reference at least one goal")
        return ProjectPlan(project.goal_ids[0], project_id, milestone_ids, task_ids)

    def actionable_tasks(self, project_id: UUID | None = None) -> tuple[Task, ...]:
        tasks = [
            t for t in self._tasks.values()
            if (project_id is None or t.project_id == project_id) and self.is_actionable(t.id)
        ]
        return tuple(sorted(
            tasks,
            key=lambda t: (
                -self._priority_rank(t),
                t.due_at is None,
                t.due_at or datetime.max.replace(tzinfo=timezone.utc),
                str(t.id),
            ),
        ))

    def overdue_tasks(self, now: datetime | None = None, project_id: UUID | None = None) -> tuple[Task, ...]:
        now = now or datetime.now(timezone.utc)
        return tuple(sorted(
            (
                t for t in self._tasks.values()
                if (project_id is None or t.project_id == project_id)
                and t.due_at is not None
                and t.due_at < now
                and t.status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED)
            ),
            key=lambda t: (t.due_at, str(t.id)),
        ))

    def snapshot(
        self,
        project_id: UUID | None = None,
        goal_id: UUID | None = None,
        now: datetime | None = None,
    ) -> PlanningSnapshot:
        project_ids = [project_id] if project_id else [
            p.id for p in self._projects.values()
            if goal_id is None or any(g == goal_id for g in p.goal_ids)
        ]
        tasks = [t for t in self._tasks.values() if t.project_id in project_ids]
        completed = sum(t.status == TaskStatus.COMPLETED for t in tasks)
        actionable_ids = tuple(
            t.id for t in self.actionable_tasks(project_id)
            if t in tasks
        )
        blocked_ids = tuple(
            t.id for t in tasks
            if t.status == TaskStatus.BLOCKED
        )
        now = now or datetime.now(timezone.utc)
        overdue_ids = tuple(
            t.id for t in tasks
            if t.due_at is not None
            and t.due_at < now
            and t.status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED)
        )
        return PlanningSnapshot(
            goal_id=goal_id,
            project_id=project_id,
            total_tasks=len(tasks),
            completed_tasks=completed,
            actionable_task_ids=actionable_ids,
            blocked_task_ids=blocked_ids,
            overdue_task_ids=overdue_ids,
            progress=(completed / len(tasks)) if tasks else 0.0,
        )

    def is_actionable(self, task_id: UUID) -> bool:
        task = self._tasks[task_id]
        if task.status not in (TaskStatus.TODO, TaskStatus.IN_PROGRESS):
            return False
        return all(self._tasks[d].status == TaskStatus.COMPLETED for d in task.dependency_ids)

    def get_task(self, task_id: UUID) -> Task:
        return self._tasks[task_id]

    def _validate_task_references(self, task: Task) -> None:
        self._require_project(task.project_id)
        if task.milestone_id is not None:
            milestone = self._milestones.get(task.milestone_id)
            if milestone is None:
                raise ValueError(f"unknown milestone: {task.milestone_id}")
            if milestone.project_id != task.project_id:
                raise ValueError("task and milestone must belong to the same project")
        for dependency_id in task.dependency_ids:
            dependency = self._tasks.get(dependency_id)
            if dependency is None:
                raise ValueError(f"unknown task dependency: {dependency_id}")
            if dependency.project_id != task.project_id:
                raise ValueError("task dependencies must belong to the same project")

    def _replace_task(self, task: Task, **changes) -> Task:
        values = {
            "title": task.title, "project_id": task.project_id, "id": task.id,
            "milestone_id": task.milestone_id, "description": task.description,
            "status": task.status, "priority": task.priority, "due_at": task.due_at,
            "dependency_ids": task.dependency_ids, "metadata": dict(task.metadata),
        }
        values.update(changes)
        return Task(**values)

    def _require_project(self, project_id: UUID) -> Project:
        if project_id not in self._projects:
            raise ValueError(f"unknown project: {project_id}")
        return self._projects[project_id]

    @staticmethod
    def _priority_rank(task: Task) -> int:
        return {"low": 1, "medium": 2, "high": 3, "critical": 4}[task.priority.value]

    def _assert_acyclic(self, project_id: UUID) -> None:
        graph = {t.id: t.dependency_ids for t in self._tasks.values() if t.project_id == project_id}
        visiting: set[UUID] = set()
        visited: set[UUID] = set()

        def visit(node: UUID) -> None:
            if node in visiting:
                raise ValueError("task dependency cycle detected")
            if node in visited:
                return
            visiting.add(node)
            for dep in graph.get(node, ()):
                visit(dep)
            visiting.remove(node)
            visited.add(node)

        for node in graph:
            visit(node)
