# PRP-02 — Architecture and production readiness audit

## Scope and evidence
Static review of repository tree and critical runtime files at commit `92e82643326f3a3f3377da159605a715efbd90cb` (PRP-01 branch). Not a penetration test, dependency vulnerability scan, exhaustive line-by-line review, or live deployment. CI run [45828522151](https://github.com/housniahmed/AHMED-AI-OS/actions/runs/45828522151) reports 51 focused and 168 full-suite tests passing. PRP-01 merge is separate.

## Findings
| ID | Severity | Evidence | Remediation / acceptance |
|---|---|---|---|
| A01 | P0 | apps/api/main.py: user/context/conversation/business/governance endpoints lack authenticated principal | Authenticate all non-public endpoints; derive actor from verified credentials; cross-user reads/writes denied in integration tests |
| A02 | P0 | apps/api/main.py ApprovalInput.approver_id; core/governance/service.py decide records caller-provided actor without authorization | Authorize approver, bind request to immutable payload and principal, enforce expiry and replay protection; negative tests |
| A03 | P0 | core/tools/gateway.py _level_allowed compares requested <= tool level; security check based on requested level | Prevent lower action level from invoking higher-impact tools even with supplied approval; test all level pairs and governance bypass paths |
| A04 | P0 | core/system/bootstrap.py GatewayActionExecutor discards governance request ID and does not forward approval; agent/runtime.py treats returned ToolResult failures as completed results | Explicit pending/approved/executed state, durable request binding and resume; denied tool result cannot be reported as success |
| A05 | P0 | Dockerfile copies core and apps, not integrations imported by API | Build image and start container; readiness smoke test |
| A06 | P0 | bootstrap uses in-memory services; compose postgres not wired to API | Inject durable repositories, migrations, transactions, restart and restore tests |
| A07 | P0 | core/persistence/postgres.py get filters by memory ID only; retrieval/security.py filters sensitivity only; agent/runtime.py retrieval query lacks user scope | Enforce trusted owner scope in repository, retrieval and model context; test cross-user access |
| A08 | P1 | bootstrap EmptyRetriever and empty ToolRegistry | Wire actual scoped retrieval and explicitly allowlisted tools; fail closed when unconfigured |
| A09 | P1 | conversation/service.py forwards only latest text; agent/runtime.py returns None when no proposals; planner observations not returned as answer | Implement grounded answer contract and scoped conversation context; test multi-turn and no-action requests |
| A10 | P1 | bootstrap creates orchestrator without planning, temporal or memory update dependencies | Compose actual services and validate end-to-end workflows |
| A11 | P1 | apps/api/main.py health always reports composed; deployment tests check files, not runtime | Separate liveness/readiness; verify configured dependencies; container and DB integration CI |
| A12 | P1 | pyproject.toml unbounded minimum dependencies, httpx2 dependency requires verification; pytest runtime dependency; no lockfile in tree | Verify intended HTTP dependency, separate test dependencies, reproducible lock and vulnerability scan |
| A13 | P1 | core/intelligence/planner.py serializes context content and source ID into model payload; no provider-specific sensitivity enforcement visible here | Data egress policy, provenance, prompt injection tests, output schema and tool argument validation |
| A14 | P2 | apps/web/app.js only fetches health and business snapshot; no authenticated chat or approvals | Secure same-origin frontend, conversation and approval views, error handling |
| A15 | P1 | core/governance/service.py can_execute reads sink.decisions despite abstract sink exposing only record | Explicit durable decision query interface and contract tests |

P0 blocks production; P1 blocks operational readiness; P2 UX. No claim of observed exploitation. A03/A04 require coordinated design, not relaxation of approval checks.

## Target architecture
Authenticated API -> request-scoped orchestrator -> scoped context/retrieval + model router -> typed proposals -> authorization and durable human approval -> execution gateway -> allowlisted adapters -> durable result/audit. Keep READ / ANALYZE / PREPARE / APPROVE / EXECUTE separate. No automatic routing policy activation.

## Remediation sequence
1. PRP-02A: identity, ownership, approval and action-level security (A01-A04,A07,A15).
2. PRP-02B: reproducible build, persistence, migrations, readiness and integration CI (A05,A06,A11,A12).
3. PRP-02C: composition, retrieval, conversation, planning and model data boundary (A08-A10,A13).
4. PRP-03: real provider benchmark with local secrets and explicit cost consent.
5. PRP-04/05/06: integrations, workflows, UI (A14); PRP-07/08 deployment and release.

## Release gates
No unresolved P0; full CI green; authenticated cross-user negative tests; immutable approval binding and replay protection; successful real container boot and DB migration; persistence across restart and restore drill; real provider benchmark; end-to-end approval workflow; secrets and dependency scan. These are acceptance criteria, not completed tests.

## Limitations
No local runtime, credentials, live database, dependency scan or external service validation was performed. Findings are based on the inspected source and CI logs; further review of remaining modules is needed. This report does not certify production readiness.
