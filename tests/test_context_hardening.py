from dataclasses import replace
from uuid import uuid4
from core.context.engine import ContextEngine
from core.retrieval.engine import HybridRetrievalEngine
from core.retrieval.models import RetrievalCandidate, RetrievalQuery, RetrievalResult

class Provider:
    def __init__(self, *items):
        self.items=list(items)
    def search(self, query):
        return self.items

def test_foreign_signal_cannot_influence_owner_candidate():
    owner=uuid4()
    c=RetrievalCandidate(uuid4(),"evidence","memory","source","internal",
        lexical_score=1,metadata={"user_id":str(owner)})
    foreign=replace(c,semantic_score=100,metadata={"user_id":str(uuid4())})
    q=RetrievalQuery("evidence",user_id=owner)
    r=HybridRetrievalEngine(Provider(c),Provider(foreign),Provider()).retrieve(q)
    assert len(r.candidates)==1
    assert r.candidates[0].semantic_score==0

def test_conflicting_authorized_identity_excluded():
    c=RetrievalCandidate(uuid4(),"first","document","source","public",lexical_score=1)
    r=HybridRetrievalEngine(Provider(c),Provider(replace(c,content="different",semantic_score=1)),Provider(c)).retrieve(RetrievalQuery("test"))
    assert not r.candidates

def test_context_metadata_detached_and_nonfinite_excluded():
    c=RetrievalCandidate(uuid4(),"evidence","document","source","public",fused_score=1,metadata={"nested":{"value":7}})
    bad=replace(c,id=uuid4(),content="invalid",fused_score=float("nan"))
    result=ContextEngine().build(RetrievalResult(RetrievalQuery("test"),(c,bad)))
    c.metadata["nested"]["value"]=99
    assert len(result.items)==1
    assert result.items[0].metadata["nested"]["value"]==7
