import os
from pathlib import Path
from uuid import uuid4
import pytest
from core.identity.models import UserIdentity
from core.persistence.connection import PostgresDatabase
from core.persistence.identity_service import PostgresIdentityService
from core.persistence.migrations import migrate

def test_identity_survives_service_recreation():
    dsn=os.getenv("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("disposable PostgreSQL required")
    db=PostgresDatabase(dsn)
    migrate(db,Path("database"))
    owner=uuid4()
    service=PostgresIdentityService(db,owner)
    service.create(UserIdentity(user_id=owner,display_name="CI owner",metadata={"test":True}))
    service.update_profile(owner,{"a":1})
    service.update_profile(owner,{"b":2})
    service.update_preferences(owner,{"locale":"fr"})
    goal=uuid4()
    service.set_active_goals(owner,[goal,goal])
    restored=PostgresIdentityService(PostgresDatabase(dsn),owner)
    assert restored.snapshot(owner).profile=={"a":1,"b":2}
    assert restored.snapshot(owner).preferences=={"locale":"fr"}
    assert restored.snapshot(owner).active_goal_ids==(goal,)
    assert restored.snapshot(owner).identity.metadata=={"test":True}
    with pytest.raises(PermissionError):
        restored.get(uuid4())
    with pytest.raises(ValueError):
        restored.create(UserIdentity(user_id=owner,display_name="duplicate"))
