"""Explicit staging composition; no migrations or execution during startup."""
import hashlib
import os
from pathlib import Path
from uuid import UUID
from core.system.bootstrap import SystemBootstrap, EmptyRetriever
from core.persistence.connection import PostgresDatabase
from core.persistence.identity_service import PostgresIdentityService
from core.persistence.memory_service import PersistentMemoryService, PostgresMemoryRetriever
from core.persistence.governance_service import DurableGovernanceService
from core.persistence.security_service import PostgresSecurityService
from core.retrieval.engine import HybridRetrievalEngine

def check_schema(db,root=Path("database")):
    files=[("001",root/"schema.sql")]+[(p.name.split("_",1)[0],p) for p in sorted((root/"migrations").glob("*.sql"))]
    expected={v:hashlib.sha256(p.read_bytes()).hexdigest() for v,p in files}
    with db.transaction() as conn, conn.cursor() as cur:
        cur.execute("SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user")
        if cur.fetchone() != (False,False):
            raise RuntimeError("privileged runtime role forbidden")
        cur.execute("""SELECT EXISTS (SELECT 1 FROM pg_roles
            WHERE rolname<>current_user AND pg_has_role(current_user,oid,'MEMBER')
            AND (rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb))""")
        if cur.fetchone()[0]:
            raise RuntimeError("privileged role membership forbidden")
        cur.execute("""SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relname=ANY(%s)
            AND c.relrowsecurity AND c.relforcerowsecurity
            AND NOT pg_has_role(current_user,c.relowner,'MEMBER')""",
            (['user_context','memories','goals','projects','approval_ledger','approval_events','security_permissions'],))
        if cur.fetchone()[0]!=7:
            raise RuntimeError("runtime table ownership or RLS configuration unsafe")
        cur.execute("SELECT version,checksum FROM schema_migrations")
        if dict(cur.fetchall()) != expected:
            raise RuntimeError("incompatible database migrations")

def build_persistent_system(model_router=None):
    owner=UUID(os.environ["AHMED_OWNER_ID"])
    if len(os.environ.get("AHMED_API_TOKEN",""))<32:
        raise ValueError("API authentication not configured")
    db=PostgresDatabase.from_env()
    check_schema(db)
    identity=PostgresIdentityService(db,owner)
    memory=PersistentMemoryService(db,owner)
    governance=DurableGovernanceService(db,owner)
    security=PostgresSecurityService(db,owner)
    # Inspect unresolved claims without retrying or mutating them.
    governance.unresolved()
    retrieval=HybridRetrievalEngine(PostgresMemoryRetriever(memory),EmptyRetriever(),EmptyRetriever())
    return SystemBootstrap(identity=identity,retrieval=retrieval,governance=governance,
        security=security,model_router=model_router).build()
