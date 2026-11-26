import os
from pathlib import Path
from uuid import uuid4

import pytest


def test_migrations_and_rls():
    dsn = os.getenv("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("disposable database required")

    from core.persistence.connection import PostgresDatabase
    from core.persistence.migrations import migrate

    db = PostgresDatabase(dsn)
    migrate(db, Path("database"))
    migrate(db, Path("database"))

    context_a, context_b = uuid4(), uuid4()
    with db.transaction() as conn, conn.cursor() as cur:
        cur.execute("CREATE ROLE ahmed_runtime LOGIN")
        cur.execute(Path("database/runtime_grants.sql").read_text())
        cur.execute(
            "INSERT INTO user_context(id) VALUES (%s), (%s)",
            (context_a, context_b),
        )

    with db.transaction(context_a) as conn, conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE ahmed_runtime")
        cur.execute("SELECT id FROM user_context")
        assert cur.fetchall() == [(context_a,)]
        cur.execute(
            "UPDATE user_context SET display_name = 'denied' WHERE id = %s",
            (context_b,),
        )
        assert cur.rowcount == 0

    with db.transaction() as conn, conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE ahmed_runtime")
        cur.execute("SELECT id FROM user_context")
        assert cur.fetchall() == []
