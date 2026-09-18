from datetime import datetime, timedelta, timezone
from core.domain.models import Memory, MemoryType, Provenance, Sensitivity
from core.memory.advanced import AdvancedMemory, MemoryQuery
from core.memory.repository import InMemoryRepository

def make(content, **kw):
    return Memory(content, MemoryType.SEMANTIC, Provenance("test","1"), **kw)

def test_recall_filters_sensitivity_and_expired():
    repo=InMemoryRepository()
    repo.save(make("research methodology", confidence=1.0))
    repo.save(make("research secret", sensitivity=Sensitivity.CONFIDENTIAL))
    repo.save(make("research expired", valid_until=datetime.now(timezone.utc)-timedelta(days=1)))
    result=AdvancedMemory(repo).recall(MemoryQuery("research", sensitivity_max=Sensitivity.INTERNAL))
    assert len(result.candidates)==1
    assert result.candidates[0].memory.content=="research methodology"

def test_recall_uses_explicit_importance():
    repo=InMemoryRepository()
    old=make("project decision", updated_at=datetime.now(timezone.utc)-timedelta(days=120), metadata={"importance":1.0})
    recent=make("project decision", metadata={"importance":0.0})
    repo.save(old); repo.save(recent)
    result=AdvancedMemory(repo).recall(MemoryQuery("project decision"))
    assert result.candidates[0].memory.id == old.id

def test_maintenance_is_non_destructive():
    repo=InMemoryRepository()
    a=make("Important decision")
    b=make("  important   decision ")
    repo.save(a); repo.save(b)
    plan=AdvancedMemory(repo).maintenance()
    assert len(plan.duplicates)==1
    assert repo.get(b.id) is not None

def test_empty_query_rejected():
    try: MemoryQuery(" ")
    except ValueError: pass
    else: raise AssertionError("empty query must be rejected")
