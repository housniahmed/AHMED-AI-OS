"""Core domain models for AHMED AI OS.

These models deliberately contain no LLM or infrastructure concerns.
They define the canonical vocabulary shared by memory, agents and tools.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MemoryType(str, Enum):
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"
    DECISION = "decision"
    PREFERENCE = "preference"
    WORKING = "working"


class Sensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class ProjectStatus(str, Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ActionLevel(str, Enum):
    READ = "read"
    ANALYZE = "analyze"
    PREPARE = "prepare"
    APPROVE = "approve"
    EXECUTE = "execute"


@dataclass(slots=True)
class Provenance:
    """Where a fact came from and how it entered the system."""

    source_type: str
    source_id: str
    captured_at: datetime = field(default_factory=utc_now)
    locator: str | None = None
    excerpt: str | None = None


@dataclass(slots=True)
class Memory:
    """A durable or temporary piece of user context."""

    content: str
    memory_type: MemoryType
    provenance: Provenance
    id: UUID = field(default_factory=uuid4)
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    confidence: float | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(slots=True)
class Goal:
    title: str
    id: UUID = field(default_factory=uuid4)
    description: str = ""
    status: str = "active"
    priority: int = 3
    deadline: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Project:
    name: str
    id: UUID = field(default_factory=uuid4)
    description: str = ""
    status: ProjectStatus = ProjectStatus.PLANNED
    goal_ids: list[UUID] = field(default_factory=list)
    memory_ids: list[UUID] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Decision:
    decision: str
    rationale: str
    id: UUID = field(default_factory=uuid4)
    project_id: UUID | None = None
    alternatives: list[str] = field(default_factory=list)
    consequences: list[str] = field(default_factory=list)
    provenance: Provenance | None = None
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class UserContext:
    """Canonical aggregate representing the user's AI-readable context."""

    user_id: UUID = field(default_factory=uuid4)
    profile: dict[str, Any] = field(default_factory=dict)
    goals: list[Goal] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    memories: list[Memory] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    preferences: dict[str, Any] = field(default_factory=dict)
    procedures: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=utc_now)
