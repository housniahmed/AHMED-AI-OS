"""Process-local human approval service; durable storage is required for production."""
from __future__ import annotations
from abc import ABC, abstractmethod
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from threading import RLock
from uuid import UUID
from .models import ApprovalDecision, ApprovalRequest, GovernanceDecision, RiskLevel

class GovernanceAuditSink(ABC):
    @abstractmethod
    def record(self, decision: GovernanceDecision) -> None: ...
    @abstractmethod
    def history(self, request_id: UUID) -> tuple[GovernanceDecision, ...]: ...

class InMemoryGovernanceAuditSink(GovernanceAuditSink):
    def __init__(self): self.decisions = []
    def record(self, decision): self.decisions.append(decision)
    def history(self, request_id):
        return tuple(d for d in self.decisions if d.request_id == request_id)

class GovernanceService:
    def __init__(self, sink=None, critical_requires_admin=True, *, ttl_seconds=900, admin_ids=()):
        if ttl_seconds <= 0: raise ValueError("approval TTL must be positive")
        self.sink = sink or InMemoryGovernanceAuditSink()
        self.critical_requires_admin = critical_requires_admin
        self.admin_ids = frozenset(admin_ids)
        self.ttl = timedelta(seconds=ttl_seconds)
        self._requests = {}
        self._expires = {}
        self._consumed = set()
        self._lock = RLock()

    def request(self, request: ApprovalRequest) -> GovernanceDecision:
        with self._lock:
            if request.id in self._requests: raise ValueError("duplicate approval request")
            self._requests[request.id] = deepcopy(request)
            self._expires[request.id] = datetime.now(timezone.utc) + self.ttl
            decision = GovernanceDecision(request.id, ApprovalDecision.PENDING, "human approval required")
            self.sink.record(decision)
            return decision

    def decide(self, request_id, decision, approver_id, *, reason=""):
        with self._lock:
            request = self.get_request(request_id)
            if approver_id != request.user_id and approver_id not in self.admin_ids:
                raise PermissionError("approver not authorized")
            if decision not in {ApprovalDecision.APPROVED, ApprovalDecision.REJECTED}:
                raise ValueError("Only approved or rejected are valid human decisions.")
            if decision is ApprovalDecision.APPROVED and request.action.risk is RiskLevel.CRITICAL and self.critical_requires_admin and approver_id not in self.admin_ids:
                raise PermissionError("critical approval requires administrator")
            if self.latest(request_id).decision is not ApprovalDecision.PENDING or datetime.now(timezone.utc) >= self._expires[request_id]:
                raise ValueError("approval is no longer pending")
            result = GovernanceDecision(request_id, decision, reason or decision.value, approver_id)
            self.sink.record(result)
            return result

    def latest(self, request_id):
        with self._lock:
            self.get_request(request_id)
            return self.sink.history(request_id)[-1]

    def can_execute(self, request_id):
        with self._lock:
            return (request_id in self._requests and request_id not in self._consumed
                    and datetime.now(timezone.utc) < self._expires[request_id]
                    and self.latest(request_id).decision is ApprovalDecision.APPROVED)

    def consume(self, request_id):
        with self._lock:
            if not self.can_execute(request_id): return False
            self._consumed.add(request_id)
            return True

    def get_request(self, request_id):
        with self._lock:
            try: return deepcopy(self._requests[request_id])
            except KeyError as exc: raise KeyError("Approval request not found.") from exc
