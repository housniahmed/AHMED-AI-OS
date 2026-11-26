import os
from pathlib import Path
from uuid import uuid4
import pytest
from core.persistence.connection import PostgresDatabase
from core.persistence.migrations import migrate
from core.persistence.identity_service import PostgresIdentityService
from core.persistence.security_service import PostgresSecurityService
from core.identity.models import UserIdentity
from core.security.models import AccessLevel, SecurityPrincipal, SecurityAction
from core.system.persistent_bootstrap import check_schema

def test_persistent_permissions():
    dsn=os.getenv("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("disposable PostgreSQL required")
    db=PostgresDatabase(dsn)
    migrate(db,Path("database"))
    owner=uuid4()
    PostgresIdentityService(db,owner).create(UserIdentity(user_id=owner,display_name="CI"))
    service=PostgresSecurityService(db,owner)
    principal=SecurityPrincipal(owner)
    action=SecurityAction("send","execute",AccessLevel.EXECUTE)
    assert not service.authorize(principal,action).allowed
    service.grant(owner,"send",AccessLevel.EXECUTE)
    restored=PostgresSecurityService(PostgresDatabase(dsn),owner)
    assert restored.authorize(principal,action).allowed
    assert not restored.authorize(SecurityPrincipal(uuid4()),action).allowed
    restored.revoke(owner,"send")
    assert not service.authorize(principal,action).allowed
    with pytest.raises(PermissionError):
        service.grant(uuid4(),"send",AccessLevel.EXECUTE)
    with pytest.raises(RuntimeError,match="privileged runtime"):
        check_schema(db)
