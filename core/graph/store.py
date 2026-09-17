"""In-memory graph store used as the reference graph contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from core.graph.models import Entity, Relationship, RelationType


class GraphStore(ABC):
    @abstractmethod
    def add_entity(self, entity: Entity) -> Entity: ...

    @abstractmethod
    def add_relationship(self, relationship: Relationship) -> Relationship: ...

    @abstractmethod
    def get_entity(self, entity_id: UUID) -> Entity: ...

    @abstractmethod
    def neighbors(self, entity_id: UUID, relation: RelationType | None = None) -> list[Entity]: ...


class InMemoryGraphStore(GraphStore):
    def __init__(self) -> None:
        self.entities: dict[UUID, Entity] = {}
        self.relationships: dict[UUID, Relationship] = {}

    def add_entity(self, entity: Entity) -> Entity:
        if entity.id in self.entities:
            raise ValueError(f"entity already exists: {entity.id}")
        self.entities[entity.id] = entity
        return entity

    def add_relationship(self, relationship: Relationship) -> Relationship:
        if relationship.source_id not in self.entities or relationship.target_id not in self.entities:
            raise ValueError("relationship endpoints must exist")
        if relationship.id in self.relationships:
            raise ValueError(f"relationship already exists: {relationship.id}")
        self.relationships[relationship.id] = relationship
        return relationship

    def get_entity(self, entity_id: UUID) -> Entity:
        return self.entities[entity_id]

    def neighbors(self, entity_id: UUID, relation: RelationType | None = None) -> list[Entity]:
        ids = []
        for edge in self.relationships.values():
            if edge.source_id == entity_id and (relation is None or edge.relation == relation):
                ids.append(edge.target_id)
            elif edge.target_id == entity_id and (relation is None or edge.relation == relation):
                ids.append(edge.source_id)
        return [self.entities[i] for i in ids]
