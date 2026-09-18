# B22 — Multi-Agent System

B22 adds provider-neutral coordination for specialized agents. It does not introduce autonomous execution or a vendor-specific agent framework.

Architecture:
USER REQUEST -> AGENT PLAN -> DEPENDENCY VALIDATION -> AGENT SELECTION -> EXECUTION -> RESULT AGGREGATION

An AgentTask declares a role and explicit dependencies. MultiAgentPlan validates and deterministically orders the dependency DAG. AgentSelector chooses an injected AgentWorker. The coordinator blocks downstream work when a dependency fails.

Invariants:
- No hidden agent-to-agent state; dependency results are explicit inputs.
- No dependency cycle is accepted.
- A worker cannot return a result for another task.
- Failed dependencies are never silently treated as successful.
- Scheduling is separate from reasoning.
- No tool/provider SDK is embedded in B22.

B22 does not replace B6 AgentRuntime. B6 remains responsible for the explicit KNOW/INFER/PROPOSE/APPROVE/EXECUTE lifecycle. B22 coordinates multiple domain workers. Governance remains separate; B18 is still pending.
