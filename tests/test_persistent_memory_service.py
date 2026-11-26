import os
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone, timedelta
import pytest
from core.domain.models import Memory, MemoryType, Provenance, Sensitivity
from core.identity.models import UserIdentity
from core.persistence.connection import PostgresDatabase
from core.persistence.identity_service import PostgresIdentityService
from core.persistence.memory_service import PersistentMemoryService, PostgresMemoryRetriever
from core.persistence.migrations import migrate
from core.retrieval.models import RetrievalQuery
from core.retrieval.engine import HybridRetrievalEngine
from core.system.bootstrap import EmptyRetriever
from core.context.engine import ContextEngine

def test_persistent_context():
    dsn=os.getenv("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("disposable PostgreSQL required")
    db=PostgresDatabase(dsn)
    migrate(db,Path("database"))
    owner,other=uuid4(),uuid4()
    for uid in (owner,other):
        PostgresIdentityService(db,uid).create(UserIdentity(user_id=uid,display_name="CI"))
    service=PersistentMemoryService(db,owner)
    good=service.save(Memory("polymer testing",MemoryType.SEMANTIC,Provenance("document","source-1")))
    service.save(Memory("polymer secret",MemoryType.SEMANTIC,Provenance("document","source-2"),sensitivity=Sensitivity.CONFIDENTIAL))
    service.save(Memory("polymer expired",MemoryType.SEMANTIC,Provenance("document","source-3"),valid_until=datetime.now(timezone.utc)-timedelta(days=1)))
    PersistentMemoryService(db,other).save(Memory("polymer foreign",MemoryType.SEMANTIC,Provenance("document","source-4"),sensitivity=Sensitivity.PUBLIC))
    restored=PersistentMemoryService(PostgresDatabase(dsn),owner)
    assert restored.get(good.id).content=="polymer testing"
    retriever=PostgresMemoryRetriever(restored)
    assert retriever.search(RetrievalQuery("polymer",user_id=other))==[]
    assert retriever.search(RetrievalQuery("polymer"))==[]
    engine=HybridRetrievalEngine(retriever,EmptyRetriever(),EmptyRetriever())
    result=engine.retrieve(RetrievalQuery("polymer",user_id=owner))
    assert [c.id for c in result.candidates]==[good.id]
    assert result.candidates[0].source_id=="source-1"
    assert ContextEngine().build(result).memories[0].content=="polymer testing"
