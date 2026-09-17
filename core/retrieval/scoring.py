"""Deterministic score fusion utilities.

The first retrieval implementation keeps ranking transparent and testable.
A production adapter can later supply BM25/vector scores without changing
this fusion contract.
"""

from __future__ import annotations

from core.retrieval.models import RetrievalCandidate


def normalize_scores(values: list[float]) -> list[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [1.0 if hi > 0 else 0.0 for _ in values]
    return [(value - lo) / (hi - lo) for value in values]


def fuse_scores(
    candidates: list[RetrievalCandidate],
    *,
    lexical_weight: float = 0.35,
    semantic_weight: float = 0.50,
    metadata_weight: float = 0.15,
) -> list[RetrievalCandidate]:
    total = lexical_weight + semantic_weight + metadata_weight
    if total <= 0:
        raise ValueError("at least one score weight must be positive")

    lw = lexical_weight / total
    sw = semantic_weight / total
    mw = metadata_weight / total

    lexical = normalize_scores([c.lexical_score for c in candidates])
    semantic = normalize_scores([c.semantic_score for c in candidates])
    metadata = normalize_scores([c.metadata_score for c in candidates])

    fused: list[RetrievalCandidate] = []
    for candidate, lx, sm, md in zip(candidates, lexical, semantic, metadata):
        score = lw * lx + sw * sm + mw * md
        fused.append(
            RetrievalCandidate(
                id=candidate.id,
                content=candidate.content,
                source_type=candidate.source_type,
                source_id=candidate.source_id,
                sensitivity=candidate.sensitivity,
                lexical_score=candidate.lexical_score,
                semantic_score=candidate.semantic_score,
                metadata_score=candidate.metadata_score,
                fused_score=score,
                metadata=candidate.metadata,
            )
        )
    return sorted(fused, key=lambda c: c.fused_score, reverse=True)
