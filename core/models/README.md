# Model Router — Brique 8

Brique 8 introduces a provider-neutral LLM gateway.

## Contract

`APPLICATION -> ModelRequest -> ModelRouter -> ModelProvider -> ModelResponse`

Routing is based on an explicit task taxonomy: chat, reasoning, extraction, classification and embedding. Each route names a provider and model and has a priority. The application never needs to know provider-specific SDK details.

The first implementation is deliberately infrastructure-light: no API keys, network calls or vendor SDKs are embedded in the core. `StaticModelProvider` exists for deterministic development and tests.

## Design principles

- Task-driven routing rather than hard-coded model calls.
- Provider abstraction for future OpenAI/Anthropic/local/other adapters.
- Explicit model selection and route priority.
- No silent fallback to an unconfigured model.
- Usage metadata is part of the response contract for later cost/latency governance.
