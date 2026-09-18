"""Canonical identity and user-context contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class UserIdentity:
    """Stable application identity; authentication remains infrastructure-specific."""

    user_id: UUID = field(default_factory=uuid4)
    display_name: str = ""
    email: str | None = None
    status: UserStatus = UserStatus.ACTIVE
    timezone: str = "UTC"
    locale: str = "en-US"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class UserContextSnapshot:
    """Bound context presented to downstream orchestration."""

    identity: UserIdentity
    profile: dict[str, Any]
    preferences: dict[str, Any]
    constraints: dict[str, Any]
    active_goal_ids: tuple[UUID, ...] = ()
    active_project_ids: tuple[UUID, ...] = ()
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class UserContextRecord:
    """Mutable application representation persisted by the identity service."""

    identity: UserIdentity
    profile: dict[str, Any] = field(default_factory=dict)
    preferences: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    active_goal_ids: list[UUID] = field(default_factory=list)
    active_project_ids: list[UUID] = field(default_factory=list)
    updated_at: datetime = field(default_factory=utc_now)

    def snapshot(self) -> UserContextSnapshot:
        return UserContextSnapshot(
            identity=self.identity,
            profile=dict(self.profile),
            preferences=dict(self.preferences),
            constraints=dict(self.constraints),
            active_goal_ids=tuple(self.active_goal_ids),
            active_project_ids=tuple(self.active_project_ids),
            updated_at=self.updated_at,
        )
