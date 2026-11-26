"""Durable approval decisions; execution remains disabled until gateway integration."""
from datetime import datetime, timezone
from uuid import UUID
from core.governance.models import (
    ApprovalDecision, ApprovalRequest, GovernanceAction, GovernanceDecision, RiskLevel,
)
from core.persistence.governance import PostgresApprovalLedger

class DurableGovernanceService:
    def __init__(self, database, owner_id, *, ttl_seconds=900):
        if ttl_seconds <= 0:
            raise ValueError("approval TTL must be positive")
        self.ledger = PostgresApprovalLedger(database, owner_id)
        self.ttl_seconds = ttl_seconds

    def request(self, request):
        self.ledger.create(request, self.ttl_seconds)
        return GovernanceDecision(request.id, ApprovalDecision.PENDING, "human approval required")

    def _row(self, request_id):
        row = self.ledger.get(request_id)
        if row is None:
            raise KeyError("Approval request not found.")
        return row

    def get_request(self, request_id):
        p = self._row(request_id)["payload"]
        action = GovernanceAction(p["name"], p["resource"], RiskLevel(p["risk"]),
                                  p["arguments"], id=UUID(p.get("action_id", str(request_id))),
                                  tool_id=UUID(p["tool_id"]), action_level=p["action_level"])
        return ApprovalRequest(action, self.ledger.owner_id, id=request_id)

    def decide(self, request_id, decision, approver_id, *, reason=""):
        if approver_id != self.ledger.owner_id:
            raise PermissionError("approver not authorized")
        if decision not in (ApprovalDecision.APPROVED, ApprovalDecision.REJECTED):
            raise ValueError("explicit approval or rejection required")
        request = self.get_request(request_id)
        if decision == ApprovalDecision.APPROVED and request.action.risk == RiskLevel.CRITICAL:
            raise PermissionError("critical approval unavailable in single-owner mode")
        if not self.ledger.decide(request_id, decision == ApprovalDecision.APPROVED):
            raise ValueError("approval is no longer pending")
        return GovernanceDecision(request_id, decision, decision.value, approver_id)

    def latest(self, request_id):
        row = self._row(request_id)
        state = row["state"]
        if state in ("pending", "approved") and row["expires_at"] <= datetime.now(timezone.utc):
            decision = ApprovalDecision.EXPIRED
        elif state in ("executing", "succeeded", "uncertain"):
            decision = ApprovalDecision.APPROVED
        else:
            decision = ApprovalDecision(state)
        actor = self.ledger.owner_id if state != "pending" else None
        return GovernanceDecision(request_id, decision, decision.value, actor)

    def history(self, request_id):
        self._row(request_id)
        with self.ledger.database.transaction(self.ledger.owner_id) as conn, conn.cursor() as cur:
            cur.execute("""SELECT state, actor_id, recorded_at FROM approval_events
                WHERE approval_id=%s ORDER BY event_id""", (request_id,))
            return tuple(dict(state=s, actor_id=a, recorded_at=t) for s,a,t in cur.fetchall())

    def can_execute(self, request_id):
        # Fail closed until B.7.4 can persist execution receipts.
        return False

    def consume(self, request_id):
        return False

    def unresolved(self):
        return self.ledger.unresolved()
