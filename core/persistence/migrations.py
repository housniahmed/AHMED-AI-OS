"""Transactional, checksum-verified migrations; run with a dedicated migration role."""
from pathlib import Path
import hashlib
from core.persistence.connection import PostgresDatabase

def migrate(database, root: Path):
    files = [("001", root / "schema.sql")]
    files += [(p.name.split("_",1)[0], p) for p in sorted((root / "migrations").glob("*.sql"))]
    versions = [v for v,p in files]
    if len(set(versions)) != len(versions) or versions != sorted(versions):
        raise ValueError("invalid migration sequence")
    with database.transaction() as conn, conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(817203)")
        cur.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
            version text PRIMARY KEY, checksum text NOT NULL,
            applied_at timestamptz NOT NULL DEFAULT clock_timestamp())""")
        cur.execute("SELECT version,checksum FROM schema_migrations ORDER BY version")
        applied = dict(cur.fetchall())
        if list(applied) != versions[:len(applied)]:
            raise RuntimeError("migration history is not a known prefix")
        for version,path in files:
            raw = path.read_bytes()
            checksum = hashlib.sha256(raw).hexdigest()
            if version in applied:
                if applied[version] != checksum:
                    raise RuntimeError(f"migration checksum mismatch: {version}")
                continue
            cur.execute(raw.decode("utf-8"))
            cur.execute("INSERT INTO schema_migrations(version,checksum) VALUES (%s,%s)",(version,checksum))

if __name__ == "__main__":
    migrate(PostgresDatabase.from_env(), Path("database"))
