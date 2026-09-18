# B16 — Unified Orchestrator

B16 is the top-level coordination boundary of AHMED AI OS.

## Flow
USER REQUEST -> IDENTITY / USER CONTEXT -> PLANNING + TEMPORAL SNAPSHOT -> AGENT RUNTIME -> APPROVAL / EXECUTION -> OPTIONAL MEMORY UPDATE

The orchestrator coordinates existing bricks; it does not duplicate the AgentRuntime state machine.

## Responsibilities
- Bind every request to an active user context.
- Collect optional planning and temporal state.
- Translate execution mode into an approval input.
- Delegate reasoning and execution to AgentRuntime.
- Return one immutable orchestration result.
- Optionally send completed results to an explicitly injected memory-update sink.

## Safety invariant
KNOW -> INFER -> PROPOSE -> APPROVE -> EXECUTE -> MEMORY UPDATE

B16 itself never calls vendor SDKs or external tools. Authentication, LLM providers, tool handlers, natural-language date parsing and autonomous memory learning remain outside this brick.
