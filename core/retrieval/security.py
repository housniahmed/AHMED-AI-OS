"""Authorization primitives for retrieval."""
from __future__ import annotations
from core.retrieval.models import RetrievalCandidate, RetrievalQuery

SENSITIVITY_ORDER = {"public": 0, "internal": 1, "confidential": 2, "restricted": 3}

def sensitivity_rank(value: str) -> int:
    if value not in SENSITIVITY_ORDER:
        raise ValueError(f"unknown sensitivity level: {value}")
    return SENSITIVITY_ORDER[value]

def filter_by_sensitivity(candidates: list[RetrievalCandidate], query: RetrievalQuery) -> list[RetrievalCandidate]:
    maximum = sensitivity_rank(query.sensitivity_max)
    return [c for c in candidates if c.sensitivity in SENSITIVITY_ORDER and sensitivity_rank(c.sensitivity) <= maximum]
