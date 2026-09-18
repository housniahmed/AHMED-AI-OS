"""Deterministic timeline and temporal query operations."""

from __future__ import annotations

from datetime import datetime, timezone
from core.temporal.models import Event, TemporalRelation


class Timeline:
    def __init__(self) -> None:
        self._events: dict[object, Event] = {}

    def add(self, event: Event) -> Event:
        if event.id in self._events:
            raise ValueError(f"event already exists: {event.id}")
        self._events[event.id] = event
        return event

    def get(self, event_id):
        return self._events[event_id]

    def all(self) -> tuple[Event, ...]:
        return tuple(sorted(self._events.values(), key=lambda e: (e.start_at, str(e.id))))

    def between(self, start_at: datetime, end_at: datetime) -> tuple[Event, ...]:
        if end_at < start_at:
            raise ValueError("end_at cannot be before start_at")
        return tuple(e for e in self.all() if e.start_at <= end_at and (e.end_at or e.start_at) >= start_at)

    def current(self, now: datetime | None = None) -> tuple[Event, ...]:
        now = now or datetime.now(timezone.utc)
        return tuple(e for e in self.all() if e.start_at <= now <= (e.end_at or e.start_at))

    def relation(self, source: Event, target: Event) -> TemporalRelation | None:
        source_end = source.end_at or source.start_at
        target_end = target.end_at or target.start_at
        if source_end < target.start_at:
            return TemporalRelation.BEFORE
        if target_end < source.start_at:
            return TemporalRelation.AFTER
        if source.start_at == target.start_at and source_end == target_end:
            return TemporalRelation.OVERLAPS
        if source.start_at <= target.start_at and source_end >= target_end:
            return TemporalRelation.DURING
        if source.start_at < target.start_at <= source_end:
            return TemporalRelation.OVERLAPS
        return None
