"""Storage abstraction for the memory layer.

The interface is intentionally infrastructure-agnostic so PostgreSQL/pgvector
can be introduced without changing domain code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from core.domain.models import Memory, MemoryType


class MemoryRepository(ABC):
    @abstractmethod
    def save(self, memory: Memory) -> Memory:
        raise NotImplementedError

    @abstractmethod
    def get(self, memory_id: UUID) -> Memory | None:
        raise NotImplementedError

    @abstractmethod
    def list_by_type(self, memory_type: MemoryType) -> list[Memory]:
        raise NotImplementedError


class InMemoryRepository(MemoryRepository):
    """Deterministic repository used for unit tests and early development."""

    def __init__(self) -> None:
        self._items: dict[UUID, Memory] = {}

    def save(self, memory: Memory) -> Memory:
        self._items[memory.id] = memory
        return memory

    def get(self, memory_id: UUID) -> Memory | None:
        return self._items.get(memory_id)

    def list_by_type(self, memory_type: MemoryType) -> list[Memory]:
        return [m for m in self._items.values() if m.memory_type == memory_type]
