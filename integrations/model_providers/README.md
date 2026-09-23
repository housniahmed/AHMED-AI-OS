# B39 — Model Reliability & Resilience

B39 adds reliability controls around the B38 multi-provider runtime.

## Controls

- Retry policy: bounded attempts with exponential backoff.
- Circuit breaker: opens after a configurable consecutive-failure threshold.
- Cooldown/recovery: an open circuit becomes eligible again after cooldown and resets on successful recovery.
- Rate-limit handling: HTTP 429 is marked rate-limited and honors the provider Retry-After header when available.
- Timeouts: each provider keeps its own request timeout from its provider settings.
- Health state: successes, failures, consecutive failures, last error, timestamps, circuit state, and cooldown are persisted through an injectable health store.
- Durability: JsonFileProviderHealthStore provides simple single-process durable persistence; production deployments can inject a database/Redis-backed implementation through the same contract.

## Runtime

Provider A -> retry -> circuit protection -> fallback -> Provider B

The router never executes tools. B6, B17, B33 and B18 remain responsible for agent execution, security and governance.

## Failure semantics

Only ModelProviderError failures enter the resilience policy. Provider adapters classify errors using retryable, rate_limited, and retry_after_seconds.

Non-retryable failures move directly to the next eligible provider.

All resilience timing is injectable in tests, so reliability tests do not need real waiting.