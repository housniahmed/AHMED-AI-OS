"""Provider-neutral scheduler domain models."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

class ScheduleKind(str, Enum):
    ONCE = "once"
    INTERVAL = "interval"

class TriggerType(str, Enum):
    TIME = "time"
    EVENT = "event"
    CONDITION = "condition"

class ScheduleState(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

@dataclass(frozen=True, slots=True)
class ScheduleDefinition:
    name: str
    trigger_type: TriggerType
    workflow_id: UUID
    id: UUID = field(default_factory=uuid4)
    kind: ScheduleKind = ScheduleKind.ONCE
    run_at: datetime | None = None
    interval_seconds: int | None = None
    event_name: str | None = None
    condition: str | None = None
    timezone: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    def __post_init__(self) -> None:
        if not self.name.strip(): raise ValueError("schedule name cannot be empty")
        if self.kind is ScheduleKind.ONCE and self.run_at is None: raise ValueError("once schedule requires run_at")
        if self.kind is ScheduleKind.INTERVAL and (self.interval_seconds is None or self.interval_seconds < 3600):
            raise ValueError("interval schedule requires interval_seconds >= 3600")
        if self.trigger_type is TriggerType.EVENT and not self.event_name: raise ValueError("event trigger requires event_name")
        if self.trigger_type is TriggerType.CONDITION and not self.condition: raise ValueError("condition trigger requires condition")

@dataclass(frozen=True, slots=True)
class ScheduleRun:
    schedule_id: UUID
    id: UUID = field(default_factory=uuid4)
    scheduled_at: datetime | None = None
    triggered_at: datetime | None = None
    workflow_run_id: UUID | None = None
    status: str = "pending"
    metadata: dict[str, Any] = field(default_factory=dict)
