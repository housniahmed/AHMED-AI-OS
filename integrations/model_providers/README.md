# B37 — Real Model Provider

B37 connects AHMED AI OS to an external model through a provider adapter while keeping the core model contracts vendor-neutral.

Architecture:

Environment / Secrets -> OpenAI-compatible adapter -> ModelProvider -> ModelRouter -> B36 ModelAgentPlanner

The adapter targets providers exposing the OpenAI-compatible POST /chat/completions contract. It is isolated under integrations/ so vendor HTTP semantics and credentials do not leak into core/.

Configuration:

- MODEL_PROVIDER_BASE_URL
- MODEL_PROVIDER_API_KEY
- MODEL_PROVIDER_MODEL
- MODEL_PROVIDER_NAME (optional; defaults to openai-compatible)
- MODEL_PROVIDER_TIMEOUT_SECONDS (optional; defaults to 30)

build_model_router_from_env() returns None when no provider variables are configured, preserving provider-free development. Partial configuration fails loudly instead of silently falling back.

Boundaries:

- Credentials are read from environment variables and never embedded in source files.
- Provider HTTP failures become explicit ModelProviderRequestError exceptions.
- The adapter never executes tools.
- B36 still produces proposals; B6, B17, B33 and B18 remain responsible for execution, security and governance.
- Embeddings are not implemented by this chat provider.
- Tests inject a fake HTTP transport and make no network calls.