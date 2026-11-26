import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from core.persistence.connection import PostgresDatabase
from core.persistence.governance import PostgresApprovalLedger
from core.governance.models import ApprovalRequest, GovernanceAction, RiskLevel

def test_durable_claim_and_owner_isolation():
    dsn = os.getenv("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("disposable TEST_DATABASE_URL required")
    db = PostgresDatabase(dsn)
    owner, other = uuid4(), uuid4()
    req = ApprovalRequest(GovernanceAction("send","send",RiskLevel.HIGH,
        {"value":7},tool_id=uuid4(),action_level="execute"),owner)
    with db.transaction() as conn, conn.cursor() as cur:
        cur.execute(Path("database/schema.sql").read_text())
        cur.execute(Path("database/migrations/002_governance.sql").read_text())
        cur.execute("INSERT INTO user_context(id) VALUES (%s),(%s)",(owner,other))
    try:
        ledger = PostgresApprovalLedger(db,owner)
        ledger.create(req)
        assert ledger.claim(req.id) is None
        foreign = PostgresApprovalLedger(db,other)
        assert foreign.get(req.id) is None
        assert not foreign.decide(req.id,True)
        assert ledger.decide(req.id,True)
        def claim(_):
            return PostgresApprovalLedger(PostgresDatabase(dsn),owner).claim(req.id)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(claim,range(2)))
        assert sum(r is not None for r in results)==1
        restarted=PostgresApprovalLedger(PostgresDatabase(dsn),owner)
        assert restarted.get(req.id)["state"]=="executing"
        assert restarted.claim(req.id) is None
        assert restarted.unresolved()==[(req.id,"executing")]
        assert restarted.finish(req.id,success=False)
        assert restarted.get(req.id)["state"]=="uncertain"
        assert restarted.claim(req.id) is None
    finally:
        with db.transaction() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM approval_events WHERE approval_id=%s",(req.id,))
            cur.execute("DELETE FROM approval_ledger WHERE id=%s",(req.id,))
            cur.execute("DELETE FROM user_context WHERE id IN (%s,%s)",(owner,other))
