import os
from uuid import uuid4
import pytest
from core.persistence.connection import PostgresDatabase
from core.persistence.identity_service import PostgresIdentityService
from core.identity.models import UserIdentity
from core.persistence.governance import PostgresApprovalLedger
from core.governance.models import ApprovalRequest, GovernanceAction, RiskLevel

def test_sql_transitions():
    dsn=os.getenv("TEST_RUNTIME_DATABASE_URL")
    if not dsn:
        pytest.skip("disposable runtime database required")
    import psycopg
    db=PostgresDatabase(dsn)
    owner=uuid4()
    PostgresIdentityService(db,owner).create(UserIdentity(user_id=owner,display_name="CI"))
    ledger=PostgresApprovalLedger(db,owner)
    req=ApprovalRequest(GovernanceAction("probe","probe",RiskLevel.HIGH,{},tool_id=uuid4(),action_level="execute"),owner)
    ledger.create(req)
    def denied(statement,params):
        with pytest.raises(psycopg.errors.RaiseException):
            with db.transaction(owner) as conn, conn.cursor() as cur:
                cur.execute(statement,params)
    denied("UPDATE approval_ledger SET state='executing',claimed_at=clock_timestamp() WHERE id=%s",(req.id,))
    assert ledger.decide(req.id,True)
    assert ledger.claim(req.id) is not None
    assert ledger.finish(req.id,success=True,receipt={"success":True})
    denied("UPDATE approval_ledger SET state='approved' WHERE id=%s",(req.id,))
    denied("UPDATE approval_ledger SET receipt='{}'::jsonb WHERE id=%s",(req.id,))
    assert ledger.get(req.id)["state"]=="succeeded"
