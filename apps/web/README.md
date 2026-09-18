# B29 — Web Dashboard

B29 defines the web dashboard boundary for AHMED AI OS. The initial implementation is a provider-neutral frontend contract and dashboard shell, designed to consume B28 without moving business logic into the UI.

## Dashboard information architecture

- Overview: system health, active goals/projects, business snapshot, upcoming events.
- Work: projects, milestones, tasks and dependencies.
- Knowledge: memories, retrieval and research evidence.
- Agents: agent activity, proposals and workflow runs.
- Business: leads, customers, offers, deals and campaigns.
- Automations: schedules and workflow state.
- Settings: identity, preferences and integration status.

The UI must present KNOW / INFER / PROPOSE / APPROVE / EXECUTE as distinct states and must never turn a proposal into an execution implicitly.
