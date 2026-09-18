"""PostgreSQL adapter for Brique 15 user context."""

from __future__ import annotations

import json
from uuid import UUID

from core.identity.models import UserContextRecord, UserIdentity, UserStatus


class PostgresUserContextRepository:
    def __init__(self, connection) -> None:
        self.connection = connection

    def save(self, record: UserContextRecord) -> UserContextRecord:
        with self.connection.cursor() as cur:
            cur.execute(
                """INSERT INTO user_context
                (id, profile, preferences, procedures, constraints)
                VALUES (%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb)
                ON CONFLICT (id) DO UPDATE SET profile=EXCLUDED.profile,
                preferences=EXCLUDED.preferences, constraints=EXCLUDED.constraints,
                updated_at=now()""",
                (
                    str(record.identity.user_id),
                    json.dumps(record.profile),
                    json.dumps(record.preferences),
                    json.dumps({}),
                    json.dumps(record.constraints),
                ),
            )
        return record

    def get(self, user_id: UUID) -> UserContextRecord | None:
        with self.connection.cursor() as cur:
            cur.execute(
                """SELECT id, profile, preferences, constraints
                FROM user_context WHERE id=%s""",
                (str(user_id),),
            )
            row = cur.fetchone()
        if row is None:
            return None
        profile=dict(row[1] or {})
        preferences=dict(row[2] or {})
        constraints=dict(row[3] or {})
        return UserContextRecord(
            identity=UserIdentity(user_id=UUID(str(row[0]))),
            profile=profile,
            preferences=preferences,
            constraints=constraints,
        )
