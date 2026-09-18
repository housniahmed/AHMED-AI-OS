"""Temporal reasoning helpers kept deterministic and explainable."""

from __future__ import annotations

from datetime import datetime, timezone
from core.temporal.models import Event, TemporalRelation


class TemporalIntelligence:
    def __init__(self, timeline) -> None:
        self.timeline = timeline

    def upcoming(self, now: datetime | None = None, limit: int = 10) -> tuple[Event, ...]:
        now = now or datetime.now(timezone.utc)
        if limit < 1:
            raise ValueError("limit must be >= 1")
        return tuple(e for e in self.timeline.all() if e.start_at >= now)[:limit]

    def overdue(self, now: datetime | None = None) -> tuple[Event, ...]:
        now = now or datetime.now(timezone.utc)
        return tuple(e for e in self.timeline.all() if e.event_type.value == "deadline" and e.start_at < now)

    def relation(self, source: Event, target: Event) -> TemporalRelation | None:
        return self.timeline.relation(source, target)
