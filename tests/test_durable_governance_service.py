import os
from pathlib import Path
from uuid import uuid4
import pytest
from core.identity.models import UserIdentity
from core.persistence.identity_service import PostgresIdentityService
from core.persistence.connection import PostgresDatabase
from core.persistence.migrations import migrate
from core.persistence.governance_service import DurableGovernanceService
from core.governance.models import ApprovalRequest, GovernanceAction, ApprovalDecision, RiskLevel

def test_durable_decision():
    dsn=os.getenv("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("disposable PostgreSQL required")
    db=PostgresDatabase(dsn)
    migrate(db,Path("database"))
    owner=uuid4()
    PostgresIdentityService(db,owner).create(UserIdentity(user_id=owner,display_name="CI"))
    service=DurableGovernanceService(db,owner)
    action=GovernanceAction("send","send",RiskLevel.HIGH,{"value":7},tool_id=uuid4(),action_level="execute")
    request=ApprovalRequest(action,owner)
    service.request(request)
    action.arguments["value"]=99
    restored=DurableGovernanceService(PostgresDatabase(dsn),owner)
    assert restored.get_request(request.id).action.arguments=={"value":7}
    assert restored.get_request(request.id).action.id==action.id
    with pytest.raises(PermissionError):
        restored.decide(request.id,ApprovalDecision.APPROVED,uuid4())
    restored.decide(request.id,ApprovalDecision.APPROVED,owner)
    assert service.latest(request.id).decision==ApprovalDecision.APPROVED
    assert [e["state"] for e in service.history(request.id)]==["pending","approved"]
    assert not restored.can_execute(request.id)
    assert not restored.consume(request.id)
    with pytest.raises(ValueError):
        restored.decide(request.id,ApprovalDecision.APPROVED,owner)
    with pytest.raises(KeyError):
        DurableGovernanceService(db,uuid4()).get_request(request.id)
