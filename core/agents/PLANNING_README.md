# B23 — Agent Planning / Task Decomposition

B23 adds a provider-neutral planning layer on top of B22.

Flow:
USER OBJECTIVE -> DECOMPOSITION REQUEST -> TASK PROPOSALS -> PLAN VALIDATION -> EXPLICIT DAG -> B22 MULTI-AGENT EXECUTION

TaskDecomposer is an injected port. It can later be backed by an LLM, rules engine, or another planner without changing B23.

AgentPlanningEngine validates task count, descriptions, priority, dependency indexes, converts indexes into explicit UUID dependencies, and rejects cycles through MultiAgentPlan.

Separation:
- B23 proposes and validates plans.
- B22 executes validated multi-agent plans.
- B6 owns the single-agent lifecycle.
- B17 governs tool execution.
- B18 Human Approval/Governance remains pending.
- Structural validity does not prove semantic plan quality.
