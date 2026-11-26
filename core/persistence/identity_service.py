from uuid import UUID
from core.identity.service import UserContextService
from core.identity.models import UserIdentity, UserStatus, UserContextRecord

class PostgresIdentityService(UserContextService):
    def __init__(self, database, owner_id):
        self.database = database
        self.owner_id = UUID(str(owner_id))

    def _scope(self, user_id):
        if user_id != self.owner_id:
            raise PermissionError("identity owner mismatch")

    def _read(self, cur, user_id):
        cur.execute("""SELECT id,display_name,email,status,timezone,locale,identity_metadata,
            profile,preferences,constraints,active_goal_ids,active_project_ids,updated_at
            FROM user_context WHERE id=%s""", (user_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return UserContextRecord(UserIdentity(row[0],row[1],row[2],UserStatus(row[3]),row[4],row[5],row[6]),
            row[7],row[8],row[9],row[10],row[11],row[12])

    def create(self, identity):
        from psycopg.types.json import Jsonb
        self._scope(identity.user_id)
        self._validate_identity(identity)
        if identity.status != UserStatus.ACTIVE:
            raise PermissionError("only active users can be created")
        with self.database.transaction(self.owner_id) as conn, conn.cursor() as cur:
            cur.execute("""INSERT INTO user_context(id,display_name,email,status,timezone,locale,identity_metadata)
                VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING RETURNING id""",
                (identity.user_id,identity.display_name,identity.email,identity.status.value,
                 identity.timezone,identity.locale,Jsonb(identity.metadata)))
            if cur.fetchone() is None:
                raise ValueError("user already exists")
            return self._read(cur,identity.user_id)

    def get(self,user_id):
        self._scope(user_id)
        with self.database.transaction(self.owner_id) as conn, conn.cursor() as cur:
            return self._read(cur,user_id)

    def snapshot(self,user_id):
        record=self.get(user_id)
        if record is None:
            raise KeyError("unknown user")
        if record.identity.status != UserStatus.ACTIVE:
            raise PermissionError("user context is not active")
        return record.snapshot()

    def _update(self,user_id,column,value,merge):
        from psycopg import sql
        from psycopg.types.json import Jsonb
        self._scope(user_id)
        with self.database.transaction(self.owner_id) as conn, conn.cursor() as cur:
            field=sql.Identifier(column)
            expression=sql.SQL("{} || %s").format(field) if merge else sql.SQL("%s::uuid[]")
            cur.execute(sql.SQL("UPDATE user_context SET {}={}, updated_at=clock_timestamp() WHERE id=%s AND status='active' RETURNING id").format(field,expression),
                (Jsonb(value) if merge else list(dict.fromkeys(value)),user_id))
            if cur.fetchone() is None:
                if self._read(cur,user_id) is None:
                    raise KeyError("unknown user")
                raise PermissionError("user context is not active")
            return self._read(cur,user_id).snapshot()

    def update_profile(self,user_id,values):
        return self._update(user_id,"profile",values,True)
    def update_preferences(self,user_id,values):
        return self._update(user_id,"preferences",values,True)
    def update_constraints(self,user_id,values):
        return self._update(user_id,"constraints",values,True)
    def set_active_goals(self,user_id,goal_ids):
        return self._update(user_id,"active_goal_ids",goal_ids,False)
    def set_active_projects(self,user_id,project_ids):
        return self._update(user_id,"active_project_ids",project_ids,False)
