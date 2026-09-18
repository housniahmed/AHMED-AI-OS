"""PostgreSQL persistence for canonical temporal Events."""

from __future__ import annotations

import json
from uuid import UUID

from core.temporal.models import Event, EventType


class PostgresEventRepository:
    def __init__(self, connection) -> None:
        self.connection = connection

    def save(self, event: Event) -> Event:
        with self.connection.cursor() as cur:
            cur.execute(
                """INSERT INTO events
                (id,name,event_type,start_at,end_at,timezone,entity_ids,provenance,metadata)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)
                ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name,
                event_type=EXCLUDED.event_type,start_at=EXCLUDED.start_at,
                end_at=EXCLUDED.end_at,timezone=EXCLUDED.timezone,
                entity_ids=EXCLUDED.entity_ids,provenance=EXCLUDED.provenance,
                metadata=EXCLUDED.metadata""",
                (str(event.id), event.name, event.event_type.value, event.start_at,
                 event.end_at, event.timezone, [str(x) for x in event.entity_ids],
                 json.dumps(event.provenance), json.dumps(event.metadata)),
            )
        return event

    def get(self, event_id: UUID) -> Event | None:
        with self.connection.cursor() as cur:
            cur.execute("""SELECT id,name,event_type,start_at,end_at,timezone,
                entity_ids,provenance,metadata FROM events WHERE id=%s""",
                (str(event_id),))
            row=cur.fetchone()
        if row is None:
            return None
        return Event(
            id=UUID(str(row[0])), name=row[1], event_type=EventType(row[2]),
            start_at=row[3], end_at=row[4], timezone=row[5],
            entity_ids=tuple(UUID(str(x)) for x in (row[6] or [])),
            provenance=dict(row[7] or {}), metadata=dict(row[8] or {}),
        )
