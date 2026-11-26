"""Run only against a disposable migrated database with runtime grants."""
import os
import subprocess
import sys
from uuid import uuid4
import pytest

WORKER = """
import os,sys
from uuid import UUID
from core.system.persistent_bootstrap import build_persistent_system
from core.identity.models import UserIdentity
from core.domain.models import Memory, MemoryType, Provenance, ActionLevel
from core.persistence.memory_service import PersistentMemoryService
from core.security.models import AccessLevel, SecurityPrincipal, SecurityAction
from core.tools.models import ToolSpec
from core.tools.permissions import ToolPermissionPolicy
from core.agent.models import AgentAction
from core.governance.models import ApprovalDecision
from core.retrieval.models import RetrievalQuery
owner=UUID(os.environ['AHMED_OWNER_ID'])
phase=sys.argv[1]
s=build_persistent_system()
s.tool_registry.register(ToolSpec('probe','test only',ActionLevel.EXECUTE,id=UUID('00000000-0000-4000-8000-000000000099')))
s.tool_runtime.policy=ToolPermissionPolicy({'probe'})
def handler(args):
    if phase=='crash':
        os._exit(73)
    assert args=={'value':7}
    return args
s.tool_runtime.bind('probe',handler)
if phase=='seed':
    s.identity.create(UserIdentity(user_id=owner,display_name='Recovery'))
    PersistentMemoryService(s.identity.database,owner).save(Memory('recovery marker',MemoryType.SEMANTIC,Provenance('test','recovery')))
    s.security.grant(owner,'probe',AccessLevel.EXECUTE)
    ids=[]
    for _ in range(3):
        rid=s.agent.executor.prepare_approval(AgentAction('probe','test','execute',{'value':7}),owner)
        ids.append(str(rid))
    s.governance.decide(UUID(ids[0]),ApprovalDecision.APPROVED,owner)
    s.governance.decide(UUID(ids[1]),ApprovalDecision.APPROVED,owner)
    print(','.join(ids))
else:
    a,b,c=map(UUID,sys.argv[2].split(','))
    assert s.identity.get(owner).identity.display_name=='Recovery'
    assert any(x.content=='recovery marker' for x in s.retrieval.retrieve(RetrievalQuery('recovery',user_id=owner)).candidates)
    assert s.security.authorize(SecurityPrincipal(owner),SecurityAction('probe','execute',AccessLevel.EXECUTE)).allowed
    assert s.governance.latest(c).decision==ApprovalDecision.PENDING
    if phase=='execute':
        assert s.gateway.resume(a,owner).result.success
    elif phase=='crash':
        s.gateway.resume(b,owner)
        raise AssertionError('crash handler not reached')
    else:
        assert s.governance.ledger.get(a)['state']=='succeeded'
        assert s.governance.ledger.get(b)['state']=='executing'
        assert (b,'executing') in s.governance.unresolved()
        assert not s.gateway.resume(a,owner).result.success
        assert not s.gateway.resume(b,owner).result.success
"""

def test_process_recovery():
    dsn=os.getenv("TEST_RUNTIME_DATABASE_URL")
    if not dsn:
        pytest.skip("disposable runtime database required")
    env=dict(os.environ,DATABASE_URL=dsn,AHMED_OWNER_ID=str(uuid4()),AHMED_API_TOKEN="ci-only-"+"x"*32)
    def run(phase,ids="",expected=0):
        result=subprocess.run([sys.executable,"-c",WORKER,phase,ids],env=env,capture_output=True,text=True,timeout=30)
        assert result.returncode==expected,result.stderr
        return result.stdout.strip()
    ids=run("seed")
    run("execute",ids)
    run("crash",ids,73)
    run("verify",ids)
