from uuid import uuid4

from core.retrieval.engine import (
    HybridRetrievalEngine,
    LexicalRetriever,
    MetadataRetriever,
    SemanticRetriever,
)
from core.retrieval.models import RetrievalCandidate, RetrievalQuery
from core.retrieval.scoring import fuse_scores
from core.retrieval.security import filter_by_sensitivity


class StaticLexical(LexicalRetriever):
    def __init__(self, candidates):
        self.candidates = candidates

    def search(self, query):
        return self.candidates


class StaticSemantic(SemanticRetriever):
    def __init__(self, candidates):
        self.candidates = candidates

    def search(self, query):
        return self.candidates


class StaticMetadata(MetadataRetriever):
    def __init__(self, candidates):
        self.candidates = candidates

    def search(self, query):
        return self.candidates


def candidate(content, *, lexical=0, semantic=0, metadata=0, sensitivity="internal"):
    return RetrievalCandidate(
        id=uuid4(),
        content=content,
        source_type="test",
        source_id="fixture",
        sensitivity=sensitivity,
        lexical_score=lexical,
        semantic_score=semantic,
        metadata_score=metadata,
    )


def test_fusion_ranks_by_combined_signal():
    first = candidate("first", lexical=1, semantic=0, metadata=0)
    second = candidate("second", lexical=0, semantic=1, metadata=0)
    ranked = fuse_scores(
        [first, second], lexical_weight=0.2, semantic_weight=0.8, metadata_weight=0
    )
    assert ranked[0].content == "second"


def test_retrieval_filters_sensitive_candidates_before_returning():
    allowed = candidate("allowed", semantic=1, sensitivity="internal")
    restricted = candidate("secret", semantic=1, sensitivity="restricted")
    query = RetrievalQuery("question", sensitivity_max="internal")
    result = filter_by_sensitivity([allowed, restricted], query)
    assert [item.content for item in result] == ["allowed"]


def test_engine_merges_provider_signals_and_preserves_top_k():
    shared = candidate("shared", lexical=0.2, semantic=0.9, metadata=0.7)
    other = candidate("other", lexical=0.9, semantic=0.1, metadata=0.1)

    query = RetrievalQuery("question", top_k=1)
    result = HybridRetrievalEngine(
        StaticLexical([shared, other]),
        StaticSemantic([shared]),
        StaticMetadata([shared]),
    ).retrieve(query)

    assert len(result.candidates) == 1
    assert result.candidates[0].content == "shared"
    assert result.citations[0]["source_id"] == "fixture"
