from core.security.service import SecurityService
from core.security.models import AccessLevel, SecurityDecision

class PostgresSecurityService(SecurityService):
    def __init__(self,database,owner_id):
        super().__init__()
        self.database=database
        self.owner_id=owner_id

    def grant(self,principal_id,resource,level):
        if principal_id != self.owner_id:
            raise PermissionError("owner mismatch")
        level=AccessLevel(level)
        with self.database.transaction(self.owner_id) as conn, conn.cursor() as cur:
            cur.execute("""INSERT INTO security_permissions VALUES (%s,%s,%s)
                ON CONFLICT(owner_id,resource) DO UPDATE SET access_level=EXCLUDED.access_level""",
                (principal_id,resource,level.value))

    def revoke(self,principal_id,resource):
        self.grant(principal_id,resource,AccessLevel.NONE)

    def authorize(self,principal,action):
        allowed=False
        if principal.user_id==self.owner_id:
            with self.database.transaction(self.owner_id) as conn, conn.cursor() as cur:
                cur.execute("SELECT access_level FROM security_permissions WHERE owner_id=%s AND resource=%s",
                    (self.owner_id,action.resource))
                row=cur.fetchone()
                allowed=row is not None and row[0]>=action.required_level.value
        decision=SecurityDecision(allowed,"authorized" if allowed else "insufficient permission",principal.user_id,action.id)
        self.sink.record(decision)
        return decision
