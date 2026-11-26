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
        from dataclasses import replace
        from math import isfinite
        by_id = {}
        conflicts = set()
        for provider, signal in ((self.lexical, "lexical_score"),
                                 (self.semantic, "semantic_score"),
                                 (self.metadata, "metadata_score")):
            for candidate in filter_by_sensitivity(provider.search(query), query):
                score = getattr(candidate, signal)
                if not isfinite(score) or candidate.id in conflicts:
                    continue
                existing = by_id.get(candidate.id)
                if existing is not None:
                    if (existing.content, existing.source_type, existing.source_id,
                        existing.sensitivity, existing.metadata) != (
                        candidate.content, candidate.source_type, candidate.source_id,
                        candidate.sensitivity, candidate.metadata):
                        conflicts.add(candidate.id)
                        del by_id[candidate.id]
                        continue
                    by_id[candidate.id] = replace(existing, **{signal: max(getattr(existing, signal), score)})
                else:
                    by_id[candidate.id] = replace(candidate, lexical_score=0.0,
                        semantic_score=0.0, metadata_score=0.0, fused_score=0.0)
                    by_id[candidate.id] = replace(by_id[candidate.id], **{signal: score})
        ranked = fuse_scores(list(by_id.values()))
        return RetrievalResult(query=query, candidates=tuple(ranked[:query.top_k]))
