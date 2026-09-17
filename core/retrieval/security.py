"""Authorization primitives for retrieval.

Filtering happens before context assembly. Retrieval must never expose a
memory that the current caller is not authorized to read.
"""

from __future__ import annotations

from core.retrieval.models import RetrievalCandidate, RetrievalQuery

SENSITIVITY_ORDER = {
    "public": 0,
    "internal": 1,
    "confidential": 2,
    "restricted": 3,
}


def filter_by_sensitivity(
    candidates: list[RetrievalCandidate], query: RetrievalQuery
) -> list[RetrievalCandidate]:
    if query.sensitivity_max not in SENSITIVITY_ORDER:
        raise ValueError(f"unknown sensitivity level: {query.sensitivity_max}")
    maximum = SENSITIVITY_ORDER[query.sensitivity_max]
    return [
        candidate
        for candidate in candidates
        if candidate.sensitivity in SENSITIVITY_ORDER
        and SENSITIVITY_ORDER[candidate.sensitivity] <= maximum
    ]
