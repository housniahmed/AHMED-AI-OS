# PRP-02B.1 — PostgreSQL persistence foundation

Memory repository now requires a trusted owner UUID at construction; all reads and type listings are owner-scoped, and conflicting IDs cannot overwrite another owner's row. Metadata is checked against the bound owner. Transaction ownership belongs to the caller. The optional postgres extra installs psycopg 3; PostgresDatabase opens and closes a connection per transaction and commits or rolls back via the driver context manager. Docker copies integrations.

Run against a disposable database only: install with python -m pip install -e ".[postgres]", set TEST_DATABASE_URL locally, then python -m pytest tests/test_postgres_memory_integration.py -v. The integration test initializes the existing schema, verifies committed data across connections and cross-owner denial. Never point it at production.

Remaining: application bootstrap still uses in-memory services, identity adapter is incomplete, planning/temporal ownership not hardened, no migration runner, no durable approval ledger, no real container readiness test, no dependency lock. No production readiness claim. Database credentials must remain outside Git. CI and actual PostgreSQL execution not verified.
