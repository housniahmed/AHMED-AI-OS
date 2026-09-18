"""Least-privilege security checks with explicit audit hooks."""
from __future__ import annotations
from abc import ABC,abstractmethod
from .models import AccessLevel,SecurityAction,SecurityDecision,SecurityPrincipal
class SecurityAuditSink(ABC):
    @abstractmethod
    def record(self,decision:SecurityDecision)->None: ...
class InMemorySecurityAuditSink(SecurityAuditSink):
    def __init__(self): self.decisions=[]
    def record(self,decision): self.decisions.append(decision)
class SecurityService:
    def __init__(self,sink:SecurityAuditSink|None=None): self.sink=sink or InMemorySecurityAuditSink(); self._permissions={}
    def grant(self,principal_id,resource,level):
        if level<AccessLevel.NONE: raise ValueError("Invalid access level.")
        self._permissions[(principal_id,resource)]=level
    def revoke(self,principal_id,resource): self._permissions.pop((principal_id,resource),None)
    def authorize(self,principal:SecurityPrincipal,action:SecurityAction)->SecurityDecision:
        granted=self._permissions.get((principal.user_id,action.resource),AccessLevel.NONE)
        allowed=granted>=action.required_level
        reason="authorized" if allowed else "insufficient permission"
        decision=SecurityDecision(allowed,reason,principal.user_id,action.id); self.sink.record(decision); return decision
