# B24 — Workflow Engine

B24 provides a provider-neutral workflow layer for durable orchestration.

Flow:
WORKFLOW DEFINITION -> VALIDATED DAG -> RUN -> STEP CHECKPOINT -> EXECUTOR -> PERSISTED STATE -> RESUME

Features:
- explicit workflow and step models;
- dependency DAG validation and deterministic topological order;
- persisted run state through WorkflowStore;
- checkpoint after workflow start, before/after each step, failure, and completion;
- resumability: completed steps are skipped on resume;
- cancellation;
- explicit step outputs and errors;
- executor injected through WorkflowStepExecutor;
- no vendor-specific SDKs and no direct external side effects in the engine.

Important separation:
- B23 creates agent task plans.
- B22 coordinates agents.
- B24 coordinates durable workflow state.
- B17 remains the tool execution gateway.
- B18 Human Approval/Governance is still pending.

The default in-memory store is for development/tests. A PostgreSQL-backed WorkflowStore should be added before production deployment. A failed step is not retried automatically; retry policy belongs to a future reliability/scheduler layer.
