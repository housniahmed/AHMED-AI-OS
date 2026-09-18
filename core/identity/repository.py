"""Persistence contract for user identity and context."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from core.identity.models import UserContextRecord


class UserContextRepository(ABC):
    @abstractmethod
    def save(self, record: UserContextRecord) -> UserContextRecord:
        raise NotImplementedError

    @abstractmethod
    def get(self, user_id: UUID) -> UserContextRecord | None:
        raise NotImplementedError


class InMemoryUserContextRepository(UserContextRepository):
    def __init__(self) -> None:
        self._items: dict[UUID, UserContextRecord] = {}

    def save(self, record: UserContextRecord) -> UserContextRecord:
        self._items[record.identity.user_id] = record
        return record

    def get(self, user_id: UUID) -> UserContextRecord | None:
        return self._items.get(user_id)
