"""Domain objects used by the retrieval layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RetrievalQuery:
    text: str
    top_k: int = 10
    memory_types: tuple[str, ...] = ()
    sensitivity_max: str = "restricted"
    project_id: UUID | None = None

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("query text cannot be empty")
        if self.top_k < 1:
            raise ValueError("top_k must be >= 1")


@dataclass(frozen=True, slots=True)
class RetrievalCandidate:
    id: UUID
    content: str
    source_type: str
    source_id: str
    sensitivity: str
    lexical_score: float = 0.0
    semantic_score: float = 0.0
    metadata_score: float = 0.0
    fused_score: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    query: RetrievalQuery
    candidates: tuple[RetrievalCandidate, ...]
    strategy: str = "hybrid"

    @property
    def citations(self) -> list[dict]:
        return [
            {
                "id": str(c.id),
                "source_type": c.source_type,
                "source_id": c.source_id,
                "metadata": c.metadata,
            }
            for c in self.candidates
        ]
