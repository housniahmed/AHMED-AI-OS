"""Opt-in integration test against a disposable PostgreSQL database."""
import os
from pathlib import Path
from uuid import uuid4
import pytest
from core.persistence.connection import PostgresDatabase
from core.persistence.postgres import PostgresMemoryRepository
from core.domain.models import Memory, MemoryType, Provenance

def test_memory_roundtrip_and_owner_isolation():
    dsn = os.getenv("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL not configured")
    db = PostgresDatabase(dsn)
    owner, other = uuid4(), uuid4()
    memory = Memory("integration test", MemoryType.SEMANTIC, Provenance("test", "test"))
    try:
        with db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(Path("database/schema.sql").read_text())
                cur.execute("INSERT INTO user_context (id) VALUES (%s),(%s)", (owner, other))
            PostgresMemoryRepository(conn, owner).save(memory)
        with db.transaction() as conn:
            repo = PostgresMemoryRepository(conn, owner)
            assert repo.get(memory.id).content == memory.content
            assert repo.list_by_type(MemoryType.SEMANTIC)[0].id == memory.id
            foreign = PostgresMemoryRepository(conn, other)
            assert foreign.get(memory.id) is None
            assert foreign.list_by_type(MemoryType.SEMANTIC) == []
            with pytest.raises(PermissionError):
                foreign.save(memory)
        with db.transaction() as conn:
            assert PostgresMemoryRepository(conn, owner).get(memory.id).content == memory.content
    finally:
        with db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM user_context WHERE id IN (%s,%s)", (owner, other))
