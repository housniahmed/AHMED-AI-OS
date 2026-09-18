"""Canonical temporal objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class EventType(str, Enum):
    TASK = "task"
    MEETING = "meeting"
    DECISION = "decision"
    MILESTONE = "milestone"
    DEADLINE = "deadline"
    OBSERVATION = "observation"
    TRANSACTION = "transaction"
    OTHER = "other"


class TemporalRelation(str, Enum):
    BEFORE = "before"
    AFTER = "after"
    DURING = "during"
    OVERLAPS = "overlaps"
    STARTS = "starts"
    ENDS = "ends"
    DEADLINE_FOR = "deadline_for"
    FOLLOWS = "follows"


@dataclass(frozen=True, slots=True)
class Event:
    name: str
    event_type: EventType
    start_at: datetime
    id: UUID = field(default_factory=uuid4)
    end_at: datetime | None = None
    timezone: str | None = None
    entity_ids: tuple[UUID, ...] = ()
    provenance: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.end_at is not None and self.end_at < self.start_at:
            raise ValueError("end_at cannot be before start_at")


@dataclass(frozen=True, slots=True)
class TemporalEdge:
    source_id: UUID
    target_id: UUID
    relation: TemporalRelation
    confidence: float | None = None
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
