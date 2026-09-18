"""PostgreSQL repository for Goal / Project / Milestone / Task state."""

from __future__ import annotations

import json
from uuid import UUID

from core.domain.models import Goal, Project, ProjectStatus
from core.planning.models import Milestone, Task, TaskPriority, TaskStatus


class PostgresPlanningRepository:
    def __init__(self, connection, user_context_id: UUID) -> None:
        self.connection = connection
        self.user_context_id = user_context_id

    def save_goal(self, goal: Goal) -> Goal:
        with self.connection.cursor() as cur:
            cur.execute(
                """INSERT INTO goals
                (id,user_context_id,title,description,status,priority,deadline,metadata)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                ON CONFLICT (id) DO UPDATE SET title=EXCLUDED.title,
                description=EXCLUDED.description,status=EXCLUDED.status,
                priority=EXCLUDED.priority,deadline=EXCLUDED.deadline,
                metadata=EXCLUDED.metadata,updated_at=now()""",
                (str(goal.id), str(self.user_context_id), goal.title, goal.description,
                 goal.status, goal.priority, goal.deadline, json.dumps(goal.metadata)),
            )
        return goal

    def save_project(self, project: Project) -> Project:
        with self.connection.cursor() as cur:
            cur.execute(
                """INSERT INTO projects
                (id,user_context_id,name,description,status,metadata)
                VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb)
                ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name,
                description=EXCLUDED.description,status=EXCLUDED.status,
                metadata=EXCLUDED.metadata,updated_at=now()""",
                (str(project.id), str(self.user_context_id), project.name, project.description,
                 project.status.value, json.dumps(project.metadata)),
            )
            cur.execute("DELETE FROM project_goals WHERE project_id=%s", (str(project.id),))
            for goal_id in project.goal_ids:
                cur.execute(
                    "INSERT INTO project_goals(project_id,goal_id) VALUES (%s,%s)",
                    (str(project.id), str(goal_id)),
                )
        return project

    def save_milestone(self, milestone: Milestone) -> Milestone:
        with self.connection.cursor() as cur:
            cur.execute(
                """INSERT INTO milestones
                (id,project_id,title,description,due_at,completed,metadata)
                VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb)
                ON CONFLICT (id) DO UPDATE SET title=EXCLUDED.title,
                description=EXCLUDED.description,due_at=EXCLUDED.due_at,
                completed=EXCLUDED.completed,metadata=EXCLUDED.metadata,
                updated_at=now()""",
                (str(milestone.id), str(milestone.project_id), milestone.title,
                 milestone.description, milestone.due_at, milestone.completed,
                 json.dumps(milestone.metadata)),
            )
        return milestone

    def save_task(self, task: Task) -> Task:
        with self.connection.cursor() as cur:
            cur.execute(
                """INSERT INTO tasks
                (id,project_id,milestone_id,title,description,status,priority,due_at,metadata)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                ON CONFLICT (id) DO UPDATE SET milestone_id=EXCLUDED.milestone_id,
                title=EXCLUDED.title,description=EXCLUDED.description,
                status=EXCLUDED.status,priority=EXCLUDED.priority,due_at=EXCLUDED.due_at,
                metadata=EXCLUDED.metadata,updated_at=now()""",
                (str(task.id), str(task.project_id),
                 str(task.milestone_id) if task.milestone_id else None,
                 task.title, task.description, task.status.value, task.priority.value,
                 task.due_at, json.dumps(task.metadata)),
            )
            cur.execute("DELETE FROM task_dependencies WHERE task_id=%s", (str(task.id),))
            for dep in task.dependency_ids:
                cur.execute(
                    "INSERT INTO task_dependencies(task_id,dependency_id) VALUES (%s,%s)",
                    (str(task.id), str(dep)),
                )
        return task

    def get_task(self, task_id: UUID) -> Task | None:
        with self.connection.cursor() as cur:
            cur.execute("""SELECT id,project_id,milestone_id,title,description,
                status,priority,due_at,metadata FROM tasks
                WHERE id=%s AND project_id IN
                (SELECT id FROM projects WHERE user_context_id=%s)""",
                (str(task_id), str(self.user_context_id)))
            row=cur.fetchone()
            if row is None:
                return None
            cur.execute("SELECT dependency_id FROM task_dependencies WHERE task_id=%s ORDER BY dependency_id",
                        (str(task_id),))
            deps=tuple(UUID(str(r[0])) for r in cur.fetchall())
        return Task(id=UUID(str(row[0])), project_id=UUID(str(row[1])),
                    milestone_id=UUID(str(row[2])) if row[2] else None, title=row[3],
                    description=row[4], status=TaskStatus(row[5]),
                    priority=TaskPriority(row[6]), due_at=row[7],
                    dependency_ids=deps, metadata=dict(row[8] or {}))

    def actionable_tasks(self, project_id: UUID) -> tuple[Task, ...]:
        # Dependency completion is evaluated in SQL against the persisted state.
        with self.connection.cursor() as cur:
            cur.execute("""SELECT t.id FROM tasks t
                WHERE t.project_id=%s AND t.status IN ('todo','in_progress')
                AND NOT EXISTS (
                    SELECT 1 FROM task_dependencies d
                    JOIN tasks dep ON dep.id=d.dependency_id
                    WHERE d.task_id=t.id AND dep.status <> 'completed'
                )
                ORDER BY CASE t.priority
                    WHEN 'critical' THEN 4 WHEN 'high' THEN 3
                    WHEN 'medium' THEN 2 ELSE 1 END DESC,
                    t.due_at NULLS LAST, t.id""", (str(project_id),))
            ids=[UUID(str(r[0])) for r in cur.fetchall()]
        return tuple(self.get_task(i) for i in ids if self.get_task(i) is not None)

    def overdue_tasks(self, project_id: UUID, now) -> tuple[Task, ...]:
        with self.connection.cursor() as cur:
            cur.execute("""SELECT id FROM tasks
                WHERE project_id=%s AND due_at IS NOT NULL AND due_at < %s
                AND status NOT IN ('completed','cancelled')
                ORDER BY due_at,id""", (str(project_id), now))
            ids=[UUID(str(r[0])) for r in cur.fetchall()]
        return tuple(self.get_task(i) for i in ids if self.get_task(i) is not None)
