# Brique 13 — Goal / Project / Task Management Engine

This module provides the planning layer of AHMED AI OS.

## Model

GOAL -> PROJECT -> MILESTONE -> TASK -> DEADLINE -> EVENT -> ACTION

The planning engine owns work state and dependencies. The temporal layer owns
time-based events. The agent runtime can consume planning snapshots and propose
actions, but planning never executes an external action.

## Capabilities

- Explicit Goal / Project / Milestone / Task hierarchy.
- Task priorities and lifecycle states.
- Dependency validation and cycle detection.
- Actionable-task detection: only TODO/IN_PROGRESS tasks whose dependencies
  are completed are actionable.
- Overdue-task detection.
- Deterministic project progress snapshots.
- Deadline adapters producing canonical temporal Event objects.
- No automatic deletion, external execution, or LLM-specific behavior.

## Invariants

1. Every project must reference existing goals.
2. Tasks and milestones must belong to an existing project.
3. Dependencies must exist and remain inside the same project.
4. Dependency cycles are rejected.
5. Starting a task is blocked while dependencies are incomplete.
6. Completed/cancelled tasks are never returned as actionable.
7. Progress is completed_tasks / total_tasks; it is descriptive, not a quality
   score or prediction.
8. Deadlines remain provenance-linked to their planning object.

## Future extensions

- Persistent repositories backed by PostgreSQL.
- Recurring tasks.
- Calendar synchronization.
- Resource/assignee constraints.
- Critical-path analysis.
- Goal health indicators based on explicit evidence rather than heuristic
  judgments.
