# Model Runtime — B8 → B40\n\nThe model runtime is provider-neutral and built incrementally from routing to reliability and usage intelligence.\n\n## B8 — Model Router\n\nThe application sends a `ModelRequest` to `ModelRouter`, which selects an explicit task/provider/model route by priority.\n\n## B36 — Model Intelligence Runtime\n\n`ModelAgentPlanner` can turn contextual information into structured reasoning and proposed actions when a model router is injected. It never executes tools.\n\n## B37 — Real Model Provider\n\n`integrations/model_providers/openai_compatible.py` provides a standard-library OpenAI-compatible adapter without embedding vendor SDKs into core.\n\n## B38 — Multi-Provider Runtime\n\nThe router supports multiple providers, task routes, priority ordering, runtime enable/disable, and fallback.\n\n## B39 — Reliability & Resilience\n\nThe router adds bounded retries, exponential backoff, circuit breaking, cooldown recovery, rate-limit handling, per-provider timeouts, and persistent health state through an injectable store.\n\n## B40 — Model Cost & Usage Intelligence\n\nB40 records one immutable usage record per provider attempt:\n\n- request ID and task\n- provider and model\n- prompt/completion/total tokens when supplied by the provider\n- provider-attempt latency\n- success/failure\n- retry attempt number\n- whether the attempt used a fallback route\n- estimated cost when pricing is configured\n- error information and request metadata\n\nThe router exposes:\n\n- `usage_records()`\n- `usage_summary()`\n- `usage_summary_by_provider()`\n- `usage_summary_by_model()`\n- `usage_summary_by_task()`\n\nThe aggregate distinguishes:\n\n- attempts vs. unique requests\n- recovered fallback requests vs. failed requests\n- token consumption\n- priced vs. unpriced attempts\n- total estimated cost\n- average provider-attempt latency\n- request error rate\n- fallback request rate\n\n### Pricing model\n\nPricing is deliberately configurable and provider-neutral through `ModelPricingCatalog`.\n\nCosts are estimates:\n\n`cost = prompt_tokens / 1,000,000 × input_price + completion_tokens / 1,000,000 × output_price`\n\nWhen pricing is not configured, the runtime records usage but returns `estimated_cost_usd=None`; it never invents a monetary value.\n\n`MODEL_PRICING_JSON` may be used by the environment-based provider factory. A durable JSON usage store can be enabled with `MODEL_USAGE_STORE_PATH`.\n\n## Boundary\n\nThe router remains responsible only for model selection/execution telemetry. It does not execute tools, approve actions, or replace B18/B33 governance and security controls.\n\n## Next logical layer\n\nB40 measures the runtime. An eventual adaptive-routing layer can consume these metrics to make explicit policy decisions across reliability, latency, quality, and cost without silently changing governance boundaries.

## B41 — Adaptive Model Routing / Policy Optimization

B41 adds an optional adaptive ranking layer above B38 priority routing.

### Decision path

`ModelRequest → eligible routes → B41 scoring → ranked routes → B39 resilience execution → B40 usage record`

For every eligible route, B41 computes four normalized dimensions:

- **Reliability**: B39 successful attempts / all observed provider attempts.
- **Latency**: derived from B40 average attempt latency.
- **Quality**: explicit `QualitySignal` supplied by an evaluator; missing quality uses a declared prior and is marked unobserved.
- **Cost**: derived from B40 estimated priced attempt cost; missing pricing uses a declared neutral score.

The final score is the weighted sum of the four dimensions. Latency and cost scores use explicit policy scales, defaulting to 1000 ms and USD 0.01 respectively. Model route priority remains only a deterministic tie-breaker after the adaptive score.

### Hard constraints

An adaptive policy may exclude routes below a minimum reliability, above a maximum latency, or above a maximum average cost. If no eligible route remains, the router fails closed with a routing error; it never silently falls back to a disallowed route.

### Quality governance

B41 does not infer model quality from successful HTTP responses. Quality comes from an explicit `QualitySignalStore`, which can later be fed by B32 evaluation or another trusted evaluator.

### Explainability

When adaptive routing is enabled, `ModelRouter.last_routing_decision()` exposes the selected route, ranked route scores and a human-readable reason. This makes provider arbitration inspectable.

### Governance boundary

B41 only chooses a model route. It does not authorize tools, approve agent actions, execute external side effects or bypass B18/B33. The existing `READ → ANALYZE → PREPARE → APPROVE → EXECUTE` governance boundary is unchanged.

### Configuration

Set `MODEL_ROUTING_MODE=adaptive` to enable B41 through the environment-based provider factory. The four weights must not all be zero. The default values preserve a balanced reliability-first policy.

B41 is intentionally deterministic. A future optimizer may use B32 evaluation results to tune policy weights, but no autonomous policy mutation is introduced here.

## B42 — Model Quality Intelligence & Evaluation Feedback Loop

B42 connects B32 evaluation evidence to B41 routing quality signals.

Flow:

`B32 EvaluationRun → QualityObservation → learned profile → QualitySignal → B41 AdaptiveRoutingEngine`

Each evaluation result must explicitly identify `provider`, `model`, and `task` in its metadata. B42 will not infer these identities from output text or network behavior.

Metric scores are combined using either configured metric weights or a simple mean. Evaluation pass/fail status is retained as evidence, but it is not used as a substitute for the metric score.

Quality learning uses a bounded exponential moving average:

`new_score = alpha × observation + (1-alpha) × previous_score`

with an explicit prior for the first observation. Confidence increases with sample count until `MODEL_QUALITY_CONFIDENCE_FULL_AT`.

B42 learns three useful levels:

- exact provider + model + task
- provider + model family + task
- model family + task across providers

Model family is preferably supplied as evaluation metadata. A small deterministic prefix resolver is available as a fallback for common family names.

B41 consumes these signals with confidence-aware blending, so a small number of evaluations cannot dominate routing.

B42 does not tune routing weights autonomously and does not authorize execution. It supplies learned quality evidence only. This preserves the separation between evaluation, policy, security, governance and execution.
