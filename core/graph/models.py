"""Provider-neutral graph entities and relationships."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class EntityType(str, Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    PROJECT = "project"
    GOAL = "goal"
    DOCUMENT = "document"
    CONCEPT = "concept"
    PRODUCT = "product"
    EVENT = "event"
    LOCATION = "location"
    OTHER = "other"


class RelationType(str, Enum):
    RELATED_TO = "related_to"
    PART_OF = "part_of"
    DEPENDS_ON = "depends_on"
    CREATED_BY = "created_by"
    OWNED_BY = "owned_by"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    REFERENCES = "references"
    HAS_GOAL = "has_goal"
    HAS_DOCUMENT = "has_document"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class Entity:
    name: str
    entity_type: EntityType
    id: UUID = field(default_factory=uuid4)
    description: str = ""
    aliases: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class Relationship:
    source_id: UUID
    target_id: UUID
    relation: RelationType
    id: UUID = field(default_factory=uuid4)
    confidence: float | None = None
    provenance: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class GraphPath:
    entity_ids: tuple[UUID, ...]
    relationship_ids: tuple[UUID, ...]
