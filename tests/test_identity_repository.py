from uuid import uuid4

from core.identity.models import UserContextRecord, UserIdentity
from core.persistence.identity import PostgresUserContextRepository


class FakeCursor:
    def __init__(self):
        self.statements = []
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, sql, params=()):
        self.statements.append((sql, params))
    def fetchone(self): return None


class FakeConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()
    def cursor(self):
        return self.cursor_obj


def test_user_context_repository_writes_context():
    conn=FakeConnection()
    record=UserContextRecord(identity=UserIdentity(user_id=uuid4(), display_name="Test"))
    repo=PostgresUserContextRepository(conn)
    assert repo.save(record) == record
    assert "INSERT INTO user_context" in conn.cursor_obj.statements[0][0]
