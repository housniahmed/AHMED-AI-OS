"""PostgreSQL persistence adapters.

The repositories use an injected DB-API connection. This keeps infrastructure
out of the domain layer and makes transaction ownership explicit: callers open,
commit, or roll back the connection/transaction.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from core.domain.models import Goal, Memory, MemoryType, Project, ProjectStatus, Provenance, Sensitivity
from core.planning.models import Milestone, Task, TaskPriority, TaskStatus
from core.temporal.models import Event, EventType


def _json(value: Any) -> str:
    return json.dumps(value, default=str)


class PostgresMemoryRepository:
    def __init__(self, connection) -> None:
        self.connection = connection

    def save(self, memory: Memory) -> Memory:
        sql = """INSERT INTO memories
        (id, user_context_id, memory_type, content, sensitivity, confidence,
         valid_from, valid_until, tags, metadata, source_type, source_id,
         source_locator, source_excerpt, captured_at, created_at, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (id) DO UPDATE SET content=EXCLUDED.content,
          sensitivity=EXCLUDED.sensitivity, confidence=EXCLUDED.confidence,
          valid_from=EXCLUDED.valid_from, valid_until=EXCLUDED.valid_until,
          tags=EXCLUDED.tags, metadata=EXCLUDED.metadata,
          source_locator=EXCLUDED.source_locator, source_excerpt=EXCLUDED.source_excerpt,
          updated_at=EXCLUDED.updated_at"""
        # user_context_id is intentionally supplied through metadata until the
        # application UserContext service binds a durable context identity.
        context_id = memory.metadata.get("user_context_id")
        if not context_id:
            raise ValueError("memory persistence requires metadata['user_context_id']")
        with self.connection.cursor() as cur:
            cur.execute(sql, (
                str(memory.id), str(context_id), memory.memory_type.value, memory.content,
                memory.sensitivity.value, memory.confidence, memory.valid_from, memory.valid_until,
                memory.tags, _json(memory.metadata), memory.provenance.source_type,
                memory.provenance.source_id, memory.provenance.locator,
                memory.provenance.excerpt, memory.provenance.captured_at,
                memory.created_at, memory.updated_at,
            ))
        return memory

    def get(self, memory_id: UUID) -> Memory | None:
        with self.connection.cursor() as cur:
            cur.execute("""SELECT id, memory_type, content, sensitivity, confidence,
                valid_from, valid_until, tags, metadata, source_type, source_id,
                source_locator, source_excerpt, captured_at, created_at, updated_at
                FROM memories WHERE id=%s""", (str(memory_id),))
            row = cur.fetchone()
        if row is None:
            return None
        return Memory(
            id=UUID(str(row[0])), memory_type=MemoryType(row[1]), content=row[2],
            sensitivity=Sensitivity(row[3]), confidence=row[4], valid_from=row[5],
            valid_until=row[6], tags=list(row[7] or []),
            metadata=dict(row[8] or {}),
            provenance=Provenance(row[9], row[10], row[13] if row[13] else row[14], row[11], row[12]),
            created_at=row[14], updated_at=row[15],
        )

    def list_by_type(self, memory_type: MemoryType) -> list[Memory]:
        raise NotImplementedError("Use list_by_type_for_context with an explicit user context")
