import os
from pathlib import Path
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import pytest
from core.identity.models import UserIdentity
from core.persistence.identity_service import PostgresIdentityService
from core.persistence.connection import PostgresDatabase
from core.persistence.migrations import migrate
from core.persistence.governance_service import DurableGovernanceService
from core.governance.models import ApprovalDecision
from core.agent.models import AgentAction
from core.domain.models import ActionLevel
from core.security.models import AccessLevel
from core.system.bootstrap import SystemBootstrap
from core.tools.models import ToolSpec
from core.tools.permissions import ToolPermissionPolicy

def test_durable_gateway():
    dsn=os.getenv("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("disposable PostgreSQL required")
    db=PostgresDatabase(dsn)
    migrate(db,Path("database"))
    owner=uuid4()
    PostgresIdentityService(db,owner).create(UserIdentity(user_id=owner,display_name="CI"))
    calls=[]
    # Explicit stable ID shared by recreated runtimes.
    tool_id=uuid4()
    def setup(fail=False):
        governance=DurableGovernanceService(PostgresDatabase(dsn),owner)
        system=SystemBootstrap(governance=governance).build()
        system.tool_registry.register(ToolSpec("send","send",ActionLevel.EXECUTE,id=tool_id))
        system.tool_runtime.policy=ToolPermissionPolicy({"send"})
        def handler(args):
            calls.append(args)
            if fail:
                raise RuntimeError("simulated provider failure")
            return args
        system.tool_runtime.bind("send",handler)
        system.security.grant(owner,"send",AccessLevel.EXECUTE)
        return system
    first=setup()
    args={"nested":{"value":7}}
    rid=first.agent.executor.prepare_approval(AgentAction("send","send","execute",args),owner)
    assert not first.gateway.resume(rid,owner).result.success
    first.governance.decide(rid,ApprovalDecision.APPROVED,owner)
    args["nested"]["value"]=99
    second=setup()
    second.security.revoke(owner,"send")
    assert not second.gateway.resume(rid,owner).result.success
    assert not calls
    second.security.grant(owner,"send",AccessLevel.EXECUTE)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda s:s.gateway.resume(rid,owner),(first,second)))
    assert sum(r.result.success for r in results)==1
    assert calls==[{"nested":{"value":7}}]
    row=second.governance.ledger.get(rid)
    assert row["state"]=="succeeded"
    assert row["receipt"]=={"call_id":str(rid),"success":True}
    assert not setup().gateway.resume(rid,owner).result.success
    failing=setup(True)
    rid2=failing.agent.executor.prepare_approval(AgentAction("send","send","execute",{}),owner)
    failing.governance.decide(rid2,ApprovalDecision.APPROVED,owner)
    assert not failing.gateway.resume(rid2,owner).result.success
    assert failing.governance.ledger.get(rid2)["state"]=="uncertain"
    assert (rid2,"uncertain") in failing.governance.unresolved()
    assert not setup().gateway.resume(rid2,owner).result.success
    assert len(calls)==2
