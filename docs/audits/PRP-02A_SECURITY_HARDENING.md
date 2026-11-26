# PRP-02A — Security hardening increment

Single-owner API bearer authentication is fail-closed without AHMED_OWNER_ID and AHMED_API_TOKEN (minimum 32 characters). Generate a high-entropy token locally, use TLS, never commit it. This is not multi-user authentication; frontend authentication is not implemented. Owner is derived from configuration, not request bodies. Health remains public.

Gateway requires exact action/tool level, explicit approval plus matching governance approval where configured, and consumes approval before execution. In-memory governance uses a 900-second TTL, authorized owner/admin, defensive copies and process-local locking. Failed tool calls no longer report completed agent state. Scoped agent retrieval filters nonpublic candidates by trusted owner metadata; actual adapters must enforce scope at source. Unscoped legacy retrieval remains for internal callers.

Remaining blockers: durable transactional approval consumption and audit, authenticated approval resume endpoint with immutable stored proposal, repository-level tenant isolation, trusted retrieval metadata, provider egress controls, TLS deployment and frontend integration. No production readiness claim. Tests must pass before merge. Do not enable external writes until these gates are met.
