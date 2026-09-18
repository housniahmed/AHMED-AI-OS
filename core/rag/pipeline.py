"""Deterministic Advanced RAG pipeline."""
from __future__ import annotations
from typing import Protocol
from core.rag.models import RAGCitation, RAGContext, RAGQuery, RAGResult
from core.retrieval.engine import HybridRetrievalEngine
from core.retrieval.models import RetrievalCandidate, RetrievalQuery

class QueryExpander(Protocol):
    def expand(self, query: str) -> tuple[str, ...]: ...

class Reranker(Protocol):
    def rerank(self, query: str, candidates: tuple[RetrievalCandidate, ...]) -> tuple[RetrievalCandidate, ...]: ...

class ContextCompressor(Protocol):
    def compress(self, query: str, candidates: tuple[RetrievalCandidate, ...], max_chars: int) -> tuple[RetrievalCandidate, ...]: ...

class AdvancedRAG:
    """Query expansion -> hybrid retrieval -> optional reranking -> compression -> citations."""
    def __init__(self, retrieval: HybridRetrievalEngine, expander: QueryExpander | None = None,
                 reranker: Reranker | None = None, compressor: ContextCompressor | None = None) -> None:
        self.retrieval, self.expander, self.reranker, self.compressor = retrieval, expander, reranker, compressor

    def run(self, query: RAGQuery) -> RAGResult:
        expanded = self._expand(query)
        merged: dict = {}
        for text in expanded:
            result = self.retrieval.retrieve(RetrievalQuery(text=text, top_k=query.top_k,
                sensitivity_max=query.sensitivity_max, project_id=query.project_id))
            for candidate in result.candidates:
                current = merged.get(candidate.id)
                if current is None or candidate.fused_score > current.fused_score:
                    merged[candidate.id] = candidate
        candidates = tuple(sorted(merged.values(), key=lambda c: (-c.fused_score, str(c.id)))[:query.top_k])
        if self.reranker is not None: candidates = self.reranker.rerank(query.text, candidates)
        if self.compressor is not None:
            selected = self.compressor.compress(query.text, candidates, query.max_context_chars)
        else:
            selected, used = [], 0
            for candidate in candidates:
                cost=len(candidate.content)
                if used + cost > query.max_context_chars: continue
                selected.append(candidate); used += cost
            selected=tuple(selected)
        citations=tuple(RAGCitation(c.source_type,c.source_id,c.metadata.get("locator"),c.metadata.get("excerpt"),c.fused_score) for c in selected)
        grounding=sum(c.fused_score for c in selected)/len(selected) if selected else 0.0
        return RAGResult(query, expanded, RAGContext(query.text, selected, citations, len(selected)<len(candidates)), max(0.0,min(1.0,grounding)))

    def _expand(self, query: RAGQuery) -> tuple[str, ...]:
        if not query.expand or self.expander is None: return (query.text,)
        values=tuple(q.strip() for q in self.expander.expand(query.text) if q.strip())
        return tuple(dict.fromkeys((query.text, *values)))
