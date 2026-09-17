"""Provider-agnostic hybrid retrieval orchestration."""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.retrieval.models import RetrievalCandidate, RetrievalQuery, RetrievalResult
from core.retrieval.scoring import fuse_scores
from core.retrieval.security import filter_by_sensitivity


class LexicalRetriever(ABC):
    @abstractmethod
    def search(self, query: RetrievalQuery) -> list[RetrievalCandidate]:
        raise NotImplementedError


class SemanticRetriever(ABC):
    @abstractmethod
    def search(self, query: RetrievalQuery) -> list[RetrievalCandidate]:
        raise NotImplementedError


class MetadataRetriever(ABC):
    @abstractmethod
    def search(self, query: RetrievalQuery) -> list[RetrievalCandidate]:
        raise NotImplementedError


class HybridRetrievalEngine:
    """Fuse independent retrieval signals into a provenance-preserving result.

    Providers are deliberately injected. This keeps the core independent of
    Elasticsearch, pgvector, a hosted embedding API, or any specific vendor.
    """

    def __init__(
        self,
        lexical: LexicalRetriever,
        semantic: SemanticRetriever,
        metadata: MetadataRetriever,
    ) -> None:
        self.lexical = lexical
        self.semantic = semantic
        self.metadata = metadata

    def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        lexical = self.lexical.search(query)
        semantic = self.semantic.search(query)
        metadata = self.metadata.search(query)

        by_id: dict = {}
        for candidate in lexical:
            by_id[candidate.id] = candidate
        for candidate in semantic:
            existing = by_id.get(candidate.id)
            if existing:
                by_id[candidate.id] = RetrievalCandidate(
                    id=existing.id,
                    content=existing.content,
                    source_type=existing.source_type,
                    source_id=existing.source_id,
                    sensitivity=existing.sensitivity,
                    lexical_score=existing.lexical_score,
                    semantic_score=candidate.semantic_score,
                    metadata_score=existing.metadata_score,
                    metadata=existing.metadata,
                )
            else:
                by_id[candidate.id] = candidate
        for candidate in metadata:
            existing = by_id.get(candidate.id)
            if existing:
                by_id[candidate.id] = RetrievalCandidate(
                    id=existing.id,
                    content=existing.content,
                    source_type=existing.source_type,
                    source_id=existing.source_id,
                    sensitivity=existing.sensitivity,
                    lexical_score=existing.lexical_score,
                    semantic_score=existing.semantic_score,
                    metadata_score=candidate.metadata_score,
                    metadata=existing.metadata,
                )
            else:
                by_id[candidate.id] = candidate

        candidates = filter_by_sensitivity(list(by_id.values()), query)
        ranked = fuse_scores(candidates)
        return RetrievalResult(query=query, candidates=tuple(ranked[: query.top_k]))
