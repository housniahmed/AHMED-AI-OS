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
                (id, display_name, email, status, timezone, locale, profile, preferences, procedures, constraints)
                VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb)
                ON CONFLICT (id) DO UPDATE SET profile=EXCLUDED.profile,
                preferences=EXCLUDED.preferences, constraints=EXCLUDED.constraints,
                updated_at=now()""",
                (
                    str(record.identity.user_id),
                    record.identity.display_name,
                    record.identity.email,
                    record.identity.status.value,
                    record.identity.timezone,
                    record.identity.locale,
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
                """SELECT id, display_name, email, status, timezone, locale,
                profile, preferences, constraints
                FROM user_context WHERE id=%s""",
                (str(user_id),),
            )
            row = cur.fetchone()
        if row is None:
            return None
        profile=dict(row[6] or {})
        preferences=dict(row[7] or {})
        constraints=dict(row[8] or {})
        return UserContextRecord(
            identity=UserIdentity(
                user_id=UUID(str(row[0])),
                display_name=row[1] or "",
                email=row[2],
                status=UserStatus(row[3]),
                timezone=row[4] or "UTC",
                locale=row[5] or "en-US",
            ),
            profile=profile,
            preferences=preferences,
            constraints=constraints,
        )
