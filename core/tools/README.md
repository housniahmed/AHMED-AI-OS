# Tool Registry, Runtime & B17 Gateway

B17 is the controlled boundary between agent proposals and registered tool handlers.

## Flow

AgentAction -> GatewayRequest -> ToolSpec validation -> ToolCall -> ToolRuntime -> ToolResult

The gateway is provider-neutral and does not know about Gmail, GitHub, Telegram, APIs, MCP servers, or vendor SDKs.

## Security invariants

1. The tool must be registered.
2. The action level must not exceed the registered tool level.
3. ToolRuntime's allow-list remains authoritative.
4. Execute-level tools require explicit approval.
5. The gateway never calls handlers directly.
6. Batch execution preserves request order and returns per-call results.

B18 will add richer human approval and governance. B17 does not implement approval workflows, roles, audit persistence, rate limiting, or secrets management.

B7 remains the registry/runtime foundation; B17 adds the explicit gateway boundary above it.
