"""Conservative memory consolidation: detect candidates, never silently overwrite."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from core.domain.models import Memory


@dataclass(frozen=True, slots=True)
class ConsolidationCandidate:
    primary_id: object
    duplicate_ids: tuple[object, ...]
    reason: str


class MemoryConsolidator:
    """Detect exact-content duplicates while preserving provenance.

    Semantic similarity and conflict resolution are intentionally deferred to
    a future embedding-backed implementation; exact matching is deterministic.
    """

    def find_exact_duplicates(self, memories: Iterable[Memory]) -> tuple[ConsolidationCandidate, ...]:
        groups: dict[tuple[str, str], list[Memory]] = {}
        for memory in memories:
            key = (memory.memory_type.value, " ".join(memory.content.lower().split()))
            groups.setdefault(key, []).append(memory)

        result: list[ConsolidationCandidate] = []
        for group in groups.values():
            if len(group) > 1:
                ordered = sorted(group, key=lambda m: (m.created_at, str(m.id)))
                result.append(ConsolidationCandidate(
                    primary_id=ordered[0].id,
                    duplicate_ids=tuple(m.id for m in ordered[1:]),
                    reason="normalized content is identical within the same memory type",
                ))
        return tuple(result)
