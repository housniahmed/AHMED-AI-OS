from uuid import uuid4
from core.rag.models import RAGQuery
from core.rag.pipeline import AdvancedRAG
from core.retrieval.models import RetrievalCandidate, RetrievalResult
from core.retrieval.engine import HybridRetrievalEngine

class R:
    def __init__(self, candidates): self.candidates=candidates
    def search(self, query): return list(self.candidates)
def candidate(text, score):
    return RetrievalCandidate(uuid4(), text, "document", text, "internal", lexical_score=score, semantic_score=score, metadata_score=score)
def test_rag_deduplicates_expanded_results_and_cites():
    c1,c2=candidate("alpha",1),candidate("beta",0.8)
    engine=HybridRetrievalEngine(R([c1,c2]),R([c1,c2]),R([c1,c2]))
    class E:
        def expand(self,q): return ("alpha","beta")
    result=AdvancedRAG(engine,E()).run(RAGQuery("alpha",top_k=5))
    assert len(result.context.passages)==2
    assert len(result.context.citations)==2
def test_rag_respects_context_budget():
    c1,c2=candidate("12345",1),candidate("67890",0.5)
    engine=HybridRetrievalEngine(R([c1,c2]),R([]),R([]))
    result=AdvancedRAG(engine).run(RAGQuery("x",top_k=5,max_context_chars=5))
    assert len(result.context.passages)==1
    assert result.context.truncated
