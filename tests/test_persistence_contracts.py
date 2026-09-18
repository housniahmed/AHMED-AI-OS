from uuid import uuid4

import pytest

from core.domain.models import Goal, Project
from core.persistence.planning import PostgresPlanningRepository


class FakeCursor:
    def __init__(self):
        self.statements = []
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, sql, params=()):
        self.statements.append((sql, params))
    def fetchone(self): return None
    def fetchall(self): return []


class FakeConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()
    def cursor(self):
        return self.cursor_obj


def test_planning_repository_writes_goal():
    connection = FakeConnection()
    context_id = uuid4()
    repo = PostgresPlanningRepository(connection, context_id)
    goal = Goal("Persist goal")
    assert repo.save_goal(goal) == goal
    assert len(connection.cursor_obj.statements) == 1
    assert "INSERT INTO goals" in connection.cursor_obj.statements[0][0]


def test_planning_repository_writes_project_and_goal_links():
    connection = FakeConnection()
    context_id = uuid4()
    goal_id = uuid4()
    project = Project("Persist project", goal_ids=[goal_id])
    repo = PostgresPlanningRepository(connection, context_id)
    assert repo.save_project(project) == project
    assert len(connection.cursor_obj.statements) == 2
    assert "project_goals" in connection.cursor_obj.statements[1][0]
