"""Explicit PostgreSQL transaction boundary; no implicit in-memory fallback."""
from contextlib import contextmanager
import os

class PostgresDatabase:
    def __init__(self, dsn: str):
        if not dsn.strip():
            raise ValueError("DATABASE_URL is required")
        self._dsn = dsn

    @classmethod
    def from_env(cls):
        return cls(os.environ.get("DATABASE_URL", ""))

    @contextmanager
    def transaction(self, owner_id=None):
        import psycopg
        with psycopg.connect(self._dsn, connect_timeout=5) as connection:
            if owner_id is not None:
                from uuid import UUID
                with connection.cursor() as cursor:
                    cursor.execute("SELECT set_config('app.owner_id', %s, true)", (str(UUID(str(owner_id))),))
            yield connection

    def check(self):
        with self.transaction() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone() == (1,)
