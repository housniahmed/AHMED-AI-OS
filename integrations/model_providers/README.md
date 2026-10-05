# Model Providers — B37 → B40\n\nThis package contains the external model-provider adapters and environment factory.\n\n## B37 — OpenAI-compatible provider\n\n`OpenAICompatibleModelProvider` calls a provider exposing an OpenAI-compatible `/chat/completions` endpoint using only the Python standard library.\n\nPer-provider timeout is configured through:\n\n- `MODEL_PROVIDER_TIMEOUT_SECONDS`\n- `MODEL_PROVIDER_<ID>_TIMEOUT_SECONDS`\n\n## B38 — Multi-provider runtime\n\nThe environment factory supports:\n\n- `MODEL_PROVIDER_IDS`\n- provider-specific base URL, API key, model and name\n- route priority\n- task allow-list\n\nThe resulting providers are connected to the core multi-provider `ModelRouter`.\n\n## B39 — Reliability\n\nThe core router adds:\n\n- bounded retries\n- exponential backoff\n- provider circuit opening after repeated failures\n- cooldown/recovery\n- HTTP 429 rate-limit classification\n- `Retry-After` handling\n- persistent provider health state\n\n## B40 — Usage and cost intelligence\n\nThe provider factory can optionally connect:\n\n- `MODEL_USAGE_STORE_PATH` → `JsonFileModelUsageStore`\n- `MODEL_PRICING_JSON` → `ModelPricingCatalog`\n\nExample pricing configuration shape:\n\n```json\n[\n  {\n    "provider": "primary",\n    "model": "model-name",\n    "input_per_1m_tokens": 1.0,\n    "output_per_1m_tokens": 2.0\n  }\n]\n```\n\nPrices are intentionally supplied by deployment configuration rather than hard-coded into the repository, because provider pricing can change.\n\nWithout pricing, token usage and latency are still recorded, while estimated monetary cost remains unknown.\n\nThe core router records both successful and failed provider attempts, allowing downstream analysis of retries, fallback usage, reliability, latency and consumption.\n\n## Security boundary\n\nAPI keys remain external configuration. They are not stored in source code or emitted into model usage records.

## B41 — Adaptive Model Routing

The provider factory can enable adaptive routing with:

- MODEL_ROUTING_MODE=adaptive
- MODEL_ROUTING_RELIABILITY_WEIGHT
- MODEL_ROUTING_LATENCY_WEIGHT
- MODEL_ROUTING_QUALITY_WEIGHT
- MODEL_ROUTING_COST_WEIGHT
- optional reliability/latency/cost hard constraints
- explicit latency and cost score scales

Priority routing remains the default when MODEL_ROUTING_MODE=priority or when the variable is unset.

Adaptive routing consumes B39 provider health state and B40 usage records. Quality is supplied separately through an injectable QualitySignalStore; the environment factory does not fabricate historical quality data.

B41 only selects and ranks model routes. It does not execute tools, approve actions, alter security permissions, or bypass governance.
