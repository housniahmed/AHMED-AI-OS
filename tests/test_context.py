from uuid import uuid4

from core.context.engine import ContextEngine
from core.retrieval.models import RetrievalCandidate, RetrievalQuery, RetrievalResult


def candidate(content, source_type="document", source_id=None, score=0.8, kind=None):
    metadata = {} if kind is None else {"kind": kind}
    return RetrievalCandidate(
        id=uuid4(),
        content=content,
        source_type=source_type,
        source_id=source_id or str(uuid4()),
        sensitivity="internal",
        fused_score=score,
        metadata=metadata,
    )


def test_context_is_grouped_by_semantic_role():
    result = RetrievalResult(
        query=RetrievalQuery("research"),
        candidates=(
            candidate("Paper evidence", score=0.9),
            candidate("A prior decision", source_type="decision", score=0.8),
            candidate("A procedure", source_type="procedure", score=0.7),
        ),
    )

    context = ContextEngine().build(result)

    assert [item.content for item in context.knowledge] == ["Paper evidence"]
    assert [item.content for item in context.decisions] == ["A prior decision"]
    assert [item.content for item in context.procedures] == ["A procedure"]


def test_context_deduplicates_and_respects_budget():
    result = RetrievalResult(
        query=RetrievalQuery("x"),
        candidates=(
            candidate("same text", source_id="doc-1", score=0.9),
            candidate("same text", source_id="doc-1", score=0.8),
            candidate("another text", source_id="doc-2", score=0.7),
        ),
    )

    context = ContextEngine(max_chars=10).build(result)

    assert len(context.items) == 1
    assert context.items[0].content == "same text"
    assert context.truncated is True
