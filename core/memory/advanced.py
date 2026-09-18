"""Advanced memory retrieval, ranking and consolidation coordination."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID
from core.domain.models import Memory, MemoryType, Sensitivity
from core.memory.consolidation import ConsolidationCandidate, MemoryConsolidator
from core.memory.lifecycle import LifecycleDecision, MemoryLifecycle
from core.retrieval.security import sensitivity_rank

class AdvancedMemoryStore(Protocol):
    def list_all(self) -> list[Memory]: ...
    def get(self, memory_id: UUID) -> Memory | None: ...

@dataclass(frozen=True, slots=True)
class MemoryQuery:
    text: str
    top_k: int = 10
    memory_types: tuple[MemoryType, ...] = ()
    sensitivity_max: Sensitivity = Sensitivity.INTERNAL
    def __post_init__(self) -> None:
        if not self.text.strip(): raise ValueError("memory query cannot be empty")
        if self.top_k < 1: raise ValueError("top_k must be >= 1")

@dataclass(frozen=True, slots=True)
class MemoryCandidate:
    memory: Memory
    lexical_score: float
    recency_score: float
    confidence_score: float
    importance_score: float
    final_score: float

@dataclass(frozen=True, slots=True)
class MemoryRecall:
    query: MemoryQuery
    candidates: tuple[MemoryCandidate, ...]

@dataclass(frozen=True, slots=True)
class MemoryMaintenancePlan:
    lifecycle: tuple[LifecycleDecision, ...]
    duplicates: tuple[ConsolidationCandidate, ...]

class AdvancedMemory:
    """Deterministic advanced-memory layer; no automatic deletion or conflict overwrite."""
    def __init__(self, store: AdvancedMemoryStore, lifecycle: MemoryLifecycle | None = None,
                 consolidator: MemoryConsolidator | None = None) -> None:
        self.store = store
        self.lifecycle = lifecycle or MemoryLifecycle()
        self.consolidator = consolidator or MemoryConsolidator()

    def recall(self, query: MemoryQuery, now: datetime | None = None) -> MemoryRecall:
        now = self._aware(now or datetime.now(timezone.utc))
        candidates = []
        for memory in self.store.list_all():
            if query.memory_types and memory.memory_type not in query.memory_types: continue
            if sensitivity_rank(memory.sensitivity) > sensitivity_rank(query.sensitivity_max): continue
            if memory.valid_until is not None and now > self._aware(memory.valid_until): continue
            lexical = self._lexical(memory.content, query.text)
            if lexical == 0.0: continue
            age_days = max(0.0, (now - self._aware(memory.updated_at)).total_seconds() / 86400)
            recency = 1.0 / (1.0 + age_days / 30.0)
            confidence = memory.confidence if memory.confidence is not None else 0.5
            importance = float(memory.metadata.get("importance", 0.5))
            importance = max(0.0, min(1.0, importance))
            final = 0.35 * lexical + 0.25 * recency + 0.20 * confidence + 0.20 * importance
            candidates.append(MemoryCandidate(memory, lexical, recency, confidence, importance, final))
        candidates.sort(key=lambda c: (-c.final_score, str(c.memory.id)))
        return MemoryRecall(query, tuple(candidates[:query.top_k]))

    def maintenance(self, now: datetime | None = None) -> MemoryMaintenancePlan:
        memories = self.store.list_all()
        return MemoryMaintenancePlan(self.lifecycle.plan(memories, now),
                                     self.consolidator.find_exact_duplicates(memories))

    @staticmethod
    def _lexical(content: str, query: str) -> float:
        content_terms, query_terms = set(content.lower().split()), set(query.lower().split())
        return len(content_terms & query_terms) / len(query_terms) if query_terms else 0.0

    @staticmethod
    def _aware(value: datetime) -> datetime:
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
