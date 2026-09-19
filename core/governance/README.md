# B18 — Human Approval / Governance

B18 is the operational governance boundary between an agent proposal and execution.

## Required flow
`Agent → PROPOSE → Governance → Human APPROVE/REJECT → Tool Gateway → EXECUTE`

## Principles
- Execution is deny-by-default until an explicit approval exists when approval is required.
- Approval is contextual and tied to a concrete approval request.
- An approval cannot be escalated into a broader permission.
- Governance does not authenticate users and does not replace B33 Security.
- Governance does not execute tools and does not replace B17 Gateway.
- Decisions are auditable.

## Scope
Approval requests are explicitly scoped to ACTION, RESOURCE or WORKFLOW. The current foundation binds approval to the request ID; broader resource/workflow delegation must be implemented with explicit semantics before use.

## Risk
Actions can declare LOW, MEDIUM, HIGH or CRITICAL risk. Risk classification is descriptive in this foundation; production policy may require stronger controls for high-risk actions.

## Current scope
In-memory governance foundation for deterministic tests. Persistent approval storage, expiry/TTL, notification channels, UI approval flows, RBAC integration with B33 and gateway enforcement are next integration steps.
