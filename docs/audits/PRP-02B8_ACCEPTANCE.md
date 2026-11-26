# PRP-02B.8 acceptance

Baseline 2051c8d: Actions run 45845839246, all five jobs successful. Logs: 51 focused tests; 174 passed/9 skipped regression; dedicated PostgreSQL 2+6+1 passed; API readiness and context HTTP 200. Focused tests overlap regression.

New gates: role membership and RLS ownership checks, receipt after process restart, database outage readiness, logical dump/restore of disposable Compose database and negative checksum check. New CI evidence pending. Restore smoke checks identity only; not full disaster recovery.

## Operating notes
Use AHMED_RUNTIME_BACKEND=postgres, AHMED_OWNER_ID, AHMED_API_TOKEN and DATABASE_URL with separate non-owner runtime credentials. Apply migrations using migration credentials, then runtime_grants.sql. Never run migrations as API runtime. Keep backups encrypted and outside the database host. Restore into an isolated database and validate data, permissions, schema and unresolved claims before switching traffic. Do not automatically replay executing/uncertain approvals.

## Remaining risks
Trusted owner GUC is not independent authentication; runtime can change it. Runtime role can modify approval state directly; SQL transition enforcement and permission administration audit remain open. Child planning tables are not fully tenant-isolated. Tool IDs must be explicitly stable; no provider exactly-once guarantee. Conversation/business/observability remain volatile. No measured RPO/RTO or full restore validation. No production readiness.

## Consolidation
Review stacked PRs in dependency order: #1, #2, #3, #4, #5, #6, #7, #8, #9, #11, #12, #13, #14, #15, #16, #17, then this acceptance branch. Verify actual bases and heads before merging; rerun CI on resulting main. No merge authorized or performed. NO-GO for production; staging acceptance conditional on new CI and outstanding P0 review.
