# B38 — Model Provider Management / Multi-Provider Runtime

B38 extends B37 from a single provider to a managed multi-provider runtime.

## Runtime behavior

- Multiple providers can be registered against the same task.
- Routes are ordered by explicit priority.
- Provider failures represented by ModelProviderError trigger deterministic fallback to the next eligible route.
- Provider state tracks enabled/disabled status, successes, failures, and the last error.
- Providers and routes can be registered or removed at runtime.
- An operator can disable a provider without changing agent code.
- An explicit ModelRequest.model continues to constrain routing to that model.

## Architecture

Provider adapters -> ModelProvider -> ModelRouter -> B36 ModelAgentPlanner

The router owns policy and fallback; provider adapters own transport/vendor semantics.

## Environment

B37 single-provider variables remain supported. For multiple providers, use MODEL_PROVIDER_IDS and namespaced variables such as PRIMARY and BACKUP.

Credentials remain environment-only. No provider secret is stored in the repository.

## Boundary

Fallback does not bypass B6, B17, B33 or B18. The router only selects a model provider and returns a model response; it never executes an agent action.
