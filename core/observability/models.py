"""Provider-neutral observability models for AHMED AI OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

def utc_now() -> datetime: return datetime.now(timezone.utc)
class EventKind(str, Enum):
    TRACE_STARTED="trace_started"; TRACE_COMPLETED="trace_completed"; TRACE_FAILED="trace_failed"; ORCHESTRATION="orchestration"; AGENT="agent"; TOOL="tool"; WORKFLOW="workflow"; MEMORY="memory"; RETRIEVAL="retrieval"; API="api"
@dataclass(frozen=True, slots=True)
class TraceContext:
    trace_id: UUID = field(default_factory=uuid4)
    parent_span_id: UUID | None = None
    span_id: UUID = field(default_factory=uuid4)
@dataclass(frozen=True, slots=True)
class AuditEvent:
    kind: EventKind; name: str; trace: TraceContext; timestamp: datetime = field(default_factory=utc_now); duration_ms: float | None = None; success: bool | None = None; user_id: UUID | None = None; correlation_id: UUID | None = None; attributes: dict[str, Any] = field(default_factory=dict); error: str | None = None
@dataclass(frozen=True, slots=True)
class MetricPoint:
    name: str; value: float; timestamp: datetime = field(default_factory=utc_now); labels: dict[str, str] = field(default_factory=dict)
