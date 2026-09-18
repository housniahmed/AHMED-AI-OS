# B25 — Event & Automation Scheduler

B25 introduces the scheduling boundary between time/event/condition triggers and workflow execution.

Flow:
TIME / EVENT / CONDITION -> SCHEDULER -> ELIGIBLE WORKFLOW -> B24 WORKFLOW ENGINE

Supported trigger types:
- TIME
- EVENT
- CONDITION

Supported schedule kinds:
- ONCE
- INTERVAL (minimum one hour)

The scheduler only determines eligibility. It does not execute workflows, tools, agents, or external actions.

Design invariants:
- no polling loop or background daemon in the core;
- no provider-specific scheduler SDK;
- explicit persisted schedule/run contracts;
- pause/cancel state;
- interval frequency is never silently increased beyond the requested cadence;
- condition evaluation is delegated to an external caller/provider;
- workflow execution remains owned by B24;
- B18 Human Approval/Governance remains pending for sensitive actions.

The current in-memory store is for development/tests. A durable PostgreSQL scheduler store and a worker/dispatch adapter belong to the deployment/reliability phase.
