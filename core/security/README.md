# B33 — Security

B33 establishes the security boundary for AHMED AI OS.

## Principles
- Least privilege.
- Deny by default.
- Explicit resource/operation authorization.
- Security decisions are separate from agent reasoning.
- Every authorization decision can be audited.
- Authentication credentials and secrets do not belong in core domain models.

## Access model
`NONE < READ < WRITE < EXECUTE < ADMIN`

A principal must have an explicit grant for the target resource at or above the action's required level. Revocation removes the grant.

## Architecture
`Identity → Security → Governance → Tool Gateway → Execution`

B33 complements B18: security answers whether a principal has permission; governance answers whether a proposed action is allowed in its operational context and whether human approval is required.

## Current scope
The implementation is provider-neutral and in-memory for deterministic testing. Production authentication, JWT/OIDC/session handling, secret management, encryption, rate limiting, network policy, durable audit storage, tenant isolation and infrastructure hardening remain deployment/security extensions.
