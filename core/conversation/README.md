# B30 — Conversational Interface

B30 defines the conversational boundary of AHMED AI OS.

Architecture:
`USER → B30 Conversation → B28 API → B16 Orchestrator → Context/Memory/RAG → Agents/Workflows → Gateway/Governance`

## Invariants
- Conversation state is separate from orchestration state.
- The interface never invokes tools directly.
- A message is not an execution command by itself.
- Provider SDKs stay outside `core/conversation`.
- If no model provider is configured, the service reports that explicitly; it does not fabricate an AI response.
- Tool execution remains subject to B17 and the planned B18 governance layer.

The current service is an in-memory bootstrap boundary. Durable conversation persistence, authentication, streaming, model-provider adapters, attachments, and production transport belong to later hardening work.
