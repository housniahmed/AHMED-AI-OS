"""Structured context objects passed from retrieval to reasoning."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ContextItem:
    """One context unit with explicit semantic role and provenance."""

    content: str
    kind: str
    source_type: str
    source_id: str
    relevance: float = 0.0
    sensitivity: str = "internal"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StructuredContext:
    """Token-budgeted context separated by meaning, not just by rank."""

    query: str
    knowledge: tuple[ContextItem, ...] = ()
    memories: tuple[ContextItem, ...] = ()
    decisions: tuple[ContextItem, ...] = ()
    goals: tuple[ContextItem, ...] = ()
    projects: tuple[ContextItem, ...] = ()
    procedures: tuple[ContextItem, ...] = ()
    truncated: bool = False

    @property
    def items(self) -> tuple[ContextItem, ...]:
        return (
            *self.knowledge,
            *self.memories,
            *self.decisions,
            *self.goals,
            *self.projects,
            *self.procedures,
        )

    @property
    def citations(self) -> list[dict[str, Any]]:
        return [
            {
                "source_type": item.source_type,
                "source_id": item.source_id,
                "kind": item.kind,
                "metadata": item.metadata,
            }
            for item in self.items
        ]
