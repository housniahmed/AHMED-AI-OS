"""Deterministic context assembly between retrieval and the LLM."""

from __future__ import annotations

from core.context.models import ContextItem, StructuredContext
from core.retrieval.models import RetrievalResult
from core.retrieval.security import filter_by_sensitivity


class ContextEngine:
    """Assemble relevant, safe, deduplicated context under a character budget.

    Character budget is an infrastructure-safe proxy for tokens at this stage.
    A tokenizer-specific budget can be introduced later without changing the
    semantic contract of StructuredContext.
    """

    def __init__(self, max_chars: int = 12000) -> None:
        if max_chars < 1:
            raise ValueError("max_chars must be >= 1")
        self.max_chars = max_chars

    def build(self, result: RetrievalResult) -> StructuredContext:
        candidates = filter_by_sensitivity(list(result.candidates), result.query)
        candidates = sorted(candidates, key=lambda item: item.fused_score, reverse=True)

        selected: list[ContextItem] = []
        seen: set[tuple[str, str, str]] = set()
        used = 0
        truncated = False

        for candidate in candidates:
            key = (candidate.source_type, candidate.source_id, candidate.content.strip())
            if key in seen:
                continue
            content = candidate.content.strip()
            if not content:
                continue
            item = ContextItem(
                content=content,
                kind=self._classify(candidate),
                source_type=candidate.source_type,
                source_id=candidate.source_id,
                relevance=candidate.fused_score,
                sensitivity=candidate.sensitivity,
                metadata=candidate.metadata,
            )
            cost = len(content)
            if used + cost > self.max_chars:
                truncated = True
                continue
            selected.append(item)
            seen.add(key)
            used += cost

        buckets = {kind: [] for kind in (
            "knowledge", "memory", "decision", "goal", "project", "procedure"
        )}
        for item in selected:
            buckets[item.kind].append(item)

        return StructuredContext(
            query=result.query.text,
            knowledge=tuple(buckets["knowledge"]),
            memories=tuple(buckets["memory"]),
            decisions=tuple(buckets["decision"]),
            goals=tuple(buckets["goal"]),
            projects=tuple(buckets["project"]),
            procedures=tuple(buckets["procedure"]),
            truncated=truncated,
        )

    @staticmethod
    def _classify(candidate) -> str:
        value = str(candidate.metadata.get("kind", "")).lower()
        if value in {"knowledge", "memory", "decision", "goal", "project", "procedure"}:
            return value
        source = candidate.source_type.lower()
        mapping = {
            "document": "knowledge",
            "document_chunk": "knowledge",
            "memory": "memory",
            "decision": "decision",
            "goal": "goal",
            "project": "project",
            "procedure": "procedure",
        }
        return mapping.get(source, "knowledge")
