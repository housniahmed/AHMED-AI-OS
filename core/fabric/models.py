"""Canonical context fabric objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class FabricNode:
    id: UUID
    kind: str
    label: str
    content: str = ""
    source_type: str | None = None
    source_id: str | None = None
    relevance: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FabricEdge:
    source_id: UUID
    target_id: UUID
    relation: str
    confidence: float | None = None
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class UnifiedContext:
    query: str
    nodes: tuple[FabricNode, ...] = ()
    edges: tuple[FabricEdge, ...] = ()
    sections: dict[str, tuple[UUID, ...]] = field(default_factory=dict)
    truncated: bool = False

    @property
    def node_by_id(self) -> dict[UUID, FabricNode]:
        return {node.id: node for node in self.nodes}
