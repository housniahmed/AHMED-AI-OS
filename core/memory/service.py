"""Application service for creating and retrieving memories."""

from __future__ import annotations

from core.domain.models import Memory, MemoryType, Provenance, Sensitivity
from core.memory.repository import MemoryRepository


class MemoryService:
    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    def remember(
        self,
        content: str,
        memory_type: MemoryType,
        source_type: str,
        source_id: str,
        *,
        sensitivity: Sensitivity = Sensitivity.INTERNAL,
        confidence: float | None = None,
        locator: str | None = None,
        excerpt: str | None = None,
        tags: list[str] | None = None,
    ) -> Memory:
        content = content.strip()
        if not content:
            raise ValueError("memory content cannot be empty")
        if not source_type.strip() or not source_id.strip():
            raise ValueError("memory provenance requires source_type and source_id")

        memory = Memory(
            content=content,
            memory_type=memory_type,
            provenance=Provenance(
                source_type=source_type,
                source_id=source_id,
                locator=locator,
                excerpt=excerpt,
            ),
            sensitivity=sensitivity,
            confidence=confidence,
            tags=tags or [],
        )
        return self.repository.save(memory)

    def get(self, memory_id):
        return self.repository.get(memory_id)

    def by_type(self, memory_type: MemoryType) -> list[Memory]:
        return self.repository.list_by_type(memory_type)
