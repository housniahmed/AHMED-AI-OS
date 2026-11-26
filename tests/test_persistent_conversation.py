import os
from uuid import uuid4
import pytest
from core.persistence.connection import PostgresDatabase
from core.persistence.identity_service import PostgresIdentityService
from core.identity.models import UserIdentity
from core.persistence.conversation_service import PostgresConversationService

def test_persistent_history():
    dsn=os.getenv("TEST_RUNTIME_DATABASE_URL")
    if not dsn:
        pytest.skip("disposable runtime database required")
    db=PostgresDatabase(dsn)
    owner,other=uuid4(),uuid4()
    for uid in (owner,other):
        PostgresIdentityService(db,uid).create(UserIdentity(user_id=uid,display_name="CI"))
    first=PostgresConversationService(db,owner)
    c=first.create(owner,"Research")
    first.send(c.id,"first question")
    class Provider:
        def respond(self,conversation,user_message):
            assert [m.content for m in conversation.messages]==["first question","second question"]
            return "answer"
    second=PostgresConversationService(PostgresDatabase(dsn),owner,Provider())
    second.send(c.id,"second question")
    assert [m.content for m in first.history(c.id)]==["first question","second question","answer"]
    foreign=PostgresConversationService(db,other)
    with pytest.raises(KeyError):
        foreign.get(c.id)
    with pytest.raises(KeyError):
        foreign.send(c.id,"forbidden")
    with pytest.raises(PermissionError):
        foreign.create(owner)
    with db.transaction(other) as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM conversation_messages WHERE conversation_id=%s",(c.id,))
        assert cur.fetchone()[0]==0
