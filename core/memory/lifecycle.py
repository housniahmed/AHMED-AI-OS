"""Memory lifecycle and consolidation policies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable

from core.domain.models import Memory, MemoryType


class MemoryOperation(str, Enum):
    CAPTURE = "capture"
    VALIDATE = "validate"
    CONSOLIDATE = "consolidate"
    UPDATE = "update"
    DECAY = "decay"
    ARCHIVE = "archive"


@dataclass(frozen=True, slots=True)
class LifecycleDecision:
    operation: MemoryOperation
    memory_id: object
    reason: str


class MemoryLifecycle:
    """Deterministic lifecycle rules; no automatic deletion is performed."""

    def __init__(self, stale_after_days: int = 180) -> None:
        if stale_after_days < 1:
            raise ValueError("stale_after_days must be >= 1")
        self.stale_after_days = stale_after_days

    def validate(self, memory: Memory) -> None:
        if not memory.content.strip():
            raise ValueError("memory content cannot be empty")
        if not memory.provenance.source_type or not memory.provenance.source_id:
            raise ValueError("memory provenance is required")
        if memory.valid_from and memory.valid_until and memory.valid_from > memory.valid_until:
            raise ValueError("valid_from cannot be after valid_until")

    def classify(self, memory: Memory) -> MemoryType:
        return memory.memory_type

    def stale(self, memory: Memory, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        reference = memory.updated_at
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=timezone.utc)
        return (now - reference).days >= self.stale_after_days

    def plan(self, memories: Iterable[Memory], now: datetime | None = None) -> tuple[LifecycleDecision, ...]:
        decisions: list[LifecycleDecision] = []
        for memory in memories:
            self.validate(memory)
            if memory.valid_until is not None and (now or datetime.now(timezone.utc)) > memory.valid_until:
                decisions.append(LifecycleDecision(MemoryOperation.ARCHIVE, memory.id, "validity window expired"))
            elif self.stale(memory, now):
                decisions.append(LifecycleDecision(MemoryOperation.DECAY, memory.id, "memory has become stale"))
            else:
                decisions.append(LifecycleDecision(MemoryOperation.VALIDATE, memory.id, "memory remains valid"))
        return tuple(decisions)
