"""Provider-neutral contracts for Advanced RAG."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID
from core.retrieval.models import RetrievalCandidate

@dataclass(frozen=True, slots=True)
class RAGQuery:
    text: str
    top_k: int = 8
    max_context_chars: int = 12000
    sensitivity_max: str = "internal"
    project_id: UUID | None = None
    expand: bool = True
    def __post_init__(self):
        if not self.text.strip(): raise ValueError("RAG query cannot be empty")
        if self.top_k < 1 or self.max_context_chars < 1: raise ValueError("top_k and max_context_chars must be >= 1")

@dataclass(frozen=True, slots=True)
class RAGCitation:
    source_type: str
    source_id: str
    locator: str | None = None
    excerpt: str | None = None
    relevance: float = 0.0

@dataclass(frozen=True, slots=True)
class RAGContext:
    query: str
    passages: tuple[RetrievalCandidate, ...]
    citations: tuple[RAGCitation, ...]
    truncated: bool = False

@dataclass(frozen=True, slots=True)
class RAGResult:
    query: RAGQuery
    expanded_queries: tuple[str, ...]
    context: RAGContext
    grounding_score: float
