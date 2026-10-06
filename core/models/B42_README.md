# B42 — Model Quality Intelligence & Evaluation Feedback Loop

B42 turns B32 evaluation evidence into learned quality signals consumed by B41.

## Feedback loop

`B32 EvaluationRun
  → explicit provider/model/task metadata
  → QualityObservation
  → learned QualityProfile
  → QualitySignal
  → B41 AdaptiveRoutingEngine`

## Evidence rules

A result is eligible for learning only when:

- provider is explicit
- model is explicit
- task is a valid `ModelTask`
- at least one `MetricResult` exists

B42 never infers quality from HTTP success, latency, cost, or model availability.

Metric scores are averaged by default or combined using configured metric weights.

## Learning

Quality profiles use a bounded exponential moving average:

`new = alpha × observation + (1-alpha) × previous`

The first observation starts from an explicit prior score.

B42 also tracks:

- sample size
- confidence
- pass rate
- latest observed score
- trend
- metric-level evidence

## Model families

B42 learns:

1. exact provider + model + task
2. provider + model family + task
3. model family + task across providers

The preferred family identity is explicit `EvaluationCase.metadata["model_family"]`. A small declared prefix resolver is available for common families such as GPT, Claude, Gemini, Llama, Mistral and Qwen.

## Persistence

`JsonFileQualityProfileStore` provides single-process durable profiles. The store is intentionally provider-neutral so it can later be replaced by PostgreSQL/Redis.

## B41 integration

`ModelQualityIntelligence` implements the B41 quality-store shape and can be passed directly to:

`AdaptiveRoutingEngine(quality_store=intelligence)`

Signals carry:

- score
- sample size
- confidence
- source
- model family

B41 blends low-confidence observations with its declared quality prior, preventing a tiny evaluation sample from dominating routing.

## Governance boundary

B42 learns evidence only. It never executes tools, grants permissions, approves actions, bypasses B18/B33, or mutates routing weights autonomously.
