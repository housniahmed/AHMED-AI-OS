# Tool Registry & Runtime — Brique 7

Brique 7 creates the controlled boundary between agent planning and external capabilities.

## Flow

`DISCOVER -> SELECT -> AUTHORIZE -> EXECUTE -> RECORD`

Every tool has an explicit `ToolSpec` with a name, description, action level and schemas. A registry exposes only registered tools. The runtime binds implementations separately from their descriptions.

The default policy is deny-by-default: a tool must be explicitly allow-listed, and tools marked `EXECUTE` additionally require explicit approval.

No provider-specific SDK is part of the core. Gmail, Calendar, GitHub, browser, filesystem and other integrations can be added later as adapters.
