"""Durable single-owner approval ledger. External calls must follow committed claims."""
import json
from uuid import UUID
from core.governance.models import ApprovalRequest, ApprovalScope, RiskLevel

class PostgresApprovalLedger:
    def __init__(self, database, owner_id: UUID):
        self.database = database
        self.owner_id = UUID(str(owner_id))

    def _event(self, cur, request_id, state):
        cur.execute("INSERT INTO approval_events (approval_id,state,actor_id) VALUES (%s,%s,%s)",
                    (request_id,state,self.owner_id))

    def create(self, request: ApprovalRequest, ttl_seconds=900):
        if request.user_id != self.owner_id:
            raise PermissionError("wrong owner")
        if ttl_seconds <= 0 or request.scope != ApprovalScope.ACTION:
            raise ValueError("invalid approval scope or TTL")
        action = request.action
        if action.tool_id is None or action.action_level not in {"approve","execute"}:
            raise ValueError("invalid tool binding")
        payload = json.dumps(dict(name=action.name, resource=action.resource,
            risk=action.risk.value, arguments=action.arguments, tool_id=str(action.tool_id),
            action_level=action.action_level), allow_nan=False)
        with self.database.transaction() as conn, conn.cursor() as cur:
            cur.execute("""INSERT INTO approval_ledger(id,owner_id,payload,expires_at)
                VALUES (%s,%s,%s::jsonb,clock_timestamp()+%s*interval '1 second')""",
                (request.id,self.owner_id,payload,ttl_seconds))
            self._event(cur,request.id,"pending")
        return request.id

    def decide(self, request_id, approved: bool):
        if type(approved) is not bool:
            raise ValueError("explicit boolean decision required")
        state = "approved" if approved else "rejected"
        with self.database.transaction() as conn, conn.cursor() as cur:
            cur.execute("""UPDATE approval_ledger SET state=%s,approver_id=%s
                WHERE id=%s AND owner_id=%s AND state='pending'
                AND expires_at>clock_timestamp()
                AND (%s=false OR (payload->>'risk')::int<4)
                RETURNING id""",(state,self.owner_id,request_id,self.owner_id,approved))
            if cur.fetchone() is None:
                return False
            self._event(cur,request_id,state)
        return True

    def claim(self, request_id):
        """Return immutable stored payload only after a successful committed claim."""
        with self.database.transaction() as conn, conn.cursor() as cur:
            cur.execute("""UPDATE approval_ledger SET state='executing',claimed_at=clock_timestamp()
                WHERE id=%s AND owner_id=%s AND state='approved'
                AND expires_at>clock_timestamp() RETURNING payload""",(request_id,self.owner_id))
            row = cur.fetchone()
            if row is None:
                return None
            self._event(cur,request_id,"executing")
        return row[0]

    def finish(self, request_id, *, success: bool, receipt=None):
        if type(success) is not bool:
            raise ValueError("explicit boolean result required")
        state = "succeeded" if success else "uncertain"
        with self.database.transaction() as conn, conn.cursor() as cur:
            cur.execute("""UPDATE approval_ledger SET state=%s,finished_at=clock_timestamp(),receipt=%s::jsonb
                WHERE id=%s AND owner_id=%s AND state='executing' RETURNING id""",
                (state,json.dumps(receipt,allow_nan=False),request_id,self.owner_id))
            if cur.fetchone() is None:
                return False
            self._event(cur,request_id,state)
        return True

    def get(self, request_id):
        with self.database.transaction() as conn, conn.cursor() as cur:
            cur.execute("""SELECT state,payload,expires_at,claimed_at,finished_at,receipt
                FROM approval_ledger WHERE id=%s AND owner_id=%s""",(request_id,self.owner_id))
            row=cur.fetchone()
        return dict(zip(("state","payload","expires_at","claimed_at","finished_at","receipt"),row)) if row else None

    def unresolved(self):
        """Report ambiguous attempts; never requeue them automatically."""
        with self.database.transaction() as conn, conn.cursor() as cur:
            cur.execute("SELECT id,state FROM approval_ledger WHERE owner_id=%s AND state IN ('executing','uncertain') ORDER BY claimed_at",(self.owner_id,))
            return cur.fetchall()
