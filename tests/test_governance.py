from uuid import uuid4
import pytest
from core.governance.models import ApprovalDecision,ApprovalRequest,GovernanceAction,RiskLevel
from core.governance.service import GovernanceService,InMemoryGovernanceAuditSink

def test_deny_by_default_until_human_approval():
    sink=InMemoryGovernanceAuditSink(); service=GovernanceService(sink); user=uuid4()
    req=ApprovalRequest(GovernanceAction("send_email","gmail.send",RiskLevel.HIGH),user)
    pending=service.request(req); assert pending.decision is ApprovalDecision.PENDING; assert not service.can_execute(req.id)
    approved=service.decide(req.id,ApprovalDecision.APPROVED,user,reason="Approved for this action")
    assert approved.decision is ApprovalDecision.APPROVED; assert service.can_execute(req.id)

def test_rejection_never_executes():
    service=GovernanceService(); user=uuid4(); req=ApprovalRequest(GovernanceAction("delete","storage.delete",RiskLevel.CRITICAL),user)
    service.request(req); service.decide(req.id,ApprovalDecision.REJECTED,user)
    assert not service.can_execute(req.id)

def test_unknown_request_rejected():
    service=GovernanceService()
    with pytest.raises(KeyError): service.decide(uuid4(),ApprovalDecision.APPROVED,uuid4())
