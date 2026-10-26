# OpenAI-Compatible Model Providers

The provider adapter connects external OpenAI-compatible chat-completions APIs to the provider-neutral core `ModelRouter`. API credentials remain deployment configuration and are not stored in source code.

## B37 — Real model provider

The adapter sends `ModelRequest` inputs to `/chat/completions` and maps returned text and token usage to `ModelResponse`. Embedding requests are rejected explicitly because this adapter does not implement embeddings.

## B38 — Multi-provider routing

The environment factory supports either one provider or multiple providers through `MODEL_PROVIDER_IDS`.

For a multi-provider setup, each ID has provider-specific values for:
- `MODEL_PROVIDER_<ID>_BASE_URL`
- `MODEL_PROVIDER_<ID>_API_KEY`
- `MODEL_PROVIDER_<ID>_MODEL`
- optional name, timeout, priority, and task allow-list

Configured routes are connected to the core `ModelRouter`. Priority routing remains the default.

## B39 — Reliability and health persistence

The router adds bounded retries, exponential backoff, circuit opening after repeated failures, cooldown recovery, HTTP 429 classification, and `Retry-After` handling.

When `MODEL_HEALTH_STORE_PATH` is configured, the environment-based factory uses `JsonFileProviderHealthStore` to persist provider health; when unset, it uses an in-memory store. The JSON file is intended for a single application process.

## B40 — Usage and cost intelligence

The provider factory can optionally connect:
- `MODEL_USAGE_STORE_PATH` → `JsonFileModelUsageStore`
- `MODEL_PRICING_JSON` → `ModelPricingCatalog`

Example pricing configuration:

```json
[
  {
    "provider": "primary",
    "model": "model-name",
    "input_per_1m_tokens": 1.0,
    "output_per_1m_tokens": 2.0
  }
]
```

Prices are supplied by deployment configuration rather than hard-coded, because provider pricing can change. Without configured prices and provider token usage, estimated monetary cost remains unknown. The router records successful and failed provider attempts so downstream analysis can evaluate retries, fallback use, reliability, latency, and consumption.

## B41 — Adaptive model routing

Set `MODEL_ROUTING_MODE=adaptive` to enable adaptive ranking. The policy supports weights for reliability, latency, quality, and cost, plus optional reliability/latency/cost hard constraints and explicit latency/cost score scales. Priority routing remains the default when the variable is unset or set to `priority`.

B41 consumes B39 provider health and B40 usage records. Quality is supplied through the explicit B42 quality signal/profile system; the environment factory does not fabricate historical quality data.

## B42 — Quality profile bootstrap

`scripts/ingest_model_quality.py` can ingest a previously collected, attributed B32 evaluation run into the durable `MODEL_QUALITY_STORE_PATH` profile store. Use an older run to build historical profiles before collecting features for a new benchmark. Profiles learned from the target benchmark must not be used as that same run's policy features.

## B43 — Routing policy learning

When `MODEL_ROUTING_MODE=adaptive`, the factory wires a `RoutingPolicyOptimizer` into `AdaptiveRoutingEngine.policy_source`. Optional persistence and gates are configured through:
- `MODEL_ROUTING_POLICY_STORE_PATH`
- `MODEL_POLICY_MIN_TRAINING_SAMPLES`
- `MODEL_POLICY_MIN_VALIDATION_SAMPLES`
- `MODEL_POLICY_MIN_MEAN_UPLIFT`
- `MODEL_POLICY_CONFIDENCE_Z`
- `MODEL_POLICY_EXPLORATION_RATE`

The benchmark workflow is documented in [B43_BENCHMARK_RUNBOOK.md](../../core/models/B43_BENCHMARK_RUNBOOK.md). It freezes historical feature evidence, runs candidates independently on the same cases, and creates reviewable proposals. A candidate is not activated unless an authenticated, authorized caller explicitly approves it against the current policy revision.

## Security boundary

API keys remain in environment configuration. They are not stored in source code or emitted into model usage records. Routing and benchmark evaluation do not authorize tool execution or bypass B18/B33 governance and security controls.
