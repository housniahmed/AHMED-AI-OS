# Brique 15 — Identity & User Context

B15 establishes the canonical application identity and the user context that
downstream orchestration may consume.

## Separation of concerns

Authentication and external identity providers are infrastructure concerns.
B15 stores the application's stable user identity and context; it does not
implement passwords, OAuth, sessions, or a specific identity provider.

## Context

A user context contains:

- identity
- profile
- preferences
- constraints
- active goals
- active projects
- update timestamp

Downstream agents should receive a snapshot rather than a mutable record.

## Safety invariants

1. User IDs are explicit UUIDs.
2. Only active users can expose an orchestration context.
3. Profile, preference and constraint updates are explicit operations.
4. Active goal/project lists are deduplicated while preserving order.
5. No authentication credential or secret is stored in this layer.
6. The identity layer does not infer user preferences from behavior.

## Future integration

B16 will bind this context to the Unified Orchestrator. PostgreSQL persistence
will be added through a dedicated adapter using the existing user_context table.
