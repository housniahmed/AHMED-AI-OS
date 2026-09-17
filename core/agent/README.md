# Agent Runtime

Brique 6 introduces the deterministic orchestration boundary between context and real-world actions.

## Contract

`KNOW -> INFER -> PROPOSE -> APPROVE -> EXECUTE`

- **KNOW**: retrieve relevant information and assemble structured context.
- **INFER**: planner interprets the request against that context.
- **PROPOSE**: planner emits explicit actions; proposals are inspectable before execution.
- **APPROVE**: policy determines whether human approval is required.
- **EXECUTE**: an injected executor performs the approved action.

The core runtime does not call an LLM, email provider, calendar, shell, or external API directly. This prevents orchestration logic from becoming coupled to vendors and makes permissions testable.

## Safety invariant

A proposed `EXECUTE` action cannot run through the default policy without an explicit `APPROVED` status.

## Next integration

Brique 7 can add concrete tool contracts and a tool registry while preserving this policy boundary.
