"""Explicit human-in-the-loop governance service."""
from __future__ import annotations
from abc import ABC,abstractmethod
from uuid import UUID
from .models import ApprovalDecision,ApprovalRequest,GovernanceDecision,RiskLevel
class GovernanceAuditSink(ABC):
    @abstractmethod
    def record(self,decision:GovernanceDecision)->None: ...
class InMemoryGovernanceAuditSink(GovernanceAuditSink):
    def __init__(self): self.decisions=[]
    def record(self,decision): self.decisions.append(decision)
class GovernanceService:
    def __init__(self,sink:GovernanceAuditSink|None=None,critical_requires_admin:bool=True):
        self.sink=sink or InMemoryGovernanceAuditSink(); self.critical_requires_admin=critical_requires_admin; self._requests={}
    def request(self,request:ApprovalRequest)->GovernanceDecision:
        self._requests[request.id]=request
        decision=GovernanceDecision(request.id,ApprovalDecision.PENDING,"human approval required")
        self.sink.record(decision); return decision
    def decide(self,request_id:UUID,decision:ApprovalDecision,approver_id:UUID,*,reason:str="")->GovernanceDecision:
        if request_id not in self._requests: raise KeyError("Approval request not found.")
        if decision not in {ApprovalDecision.APPROVED,ApprovalDecision.REJECTED}: raise ValueError("Only approved or rejected are valid human decisions.")
        result=GovernanceDecision(request_id,decision,reason or decision.value,approver_id); self.sink.record(result); return result
    def can_execute(self,request_id:UUID)->bool:
        decisions=[d for d in self.sink.decisions if d.request_id==request_id]
        return bool(decisions) and decisions[-1].decision is ApprovalDecision.APPROVED
    def get_request(self,request_id:UUID)->ApprovalRequest:
        try:return self._requests[request_id]
        except KeyError as exc: raise KeyError("Approval request not found.") from exc
