# B32 — Evaluation Framework

B32 defines the evaluation boundary for AHMED AI OS.

## Purpose
Evaluation measures observable behavior; it does not silently alter execution policy or claim that a score is truth.

## Supported structure
`EvaluationCase → Runner → EvaluationMetric(s) → EvaluationResult → EvaluationRun → Summary`

Metrics are injectable and normalized to [0,1]. Thresholds are explicit. A passing score means only that the configured metric condition was met for that test case.

## Applicable domains
- Conversational responses
- Retrieval / RAG grounding
- Research Guardian claim-source matching
- Agent planning and decomposition
- Workflow behavior
- Tool/gateway behavior
- Business workflows

## Invariants
- No fabricated benchmark results.
- No universal quality score is assumed.
- Metric definitions and thresholds must be documented.
- Evaluation is separate from authorization and execution.
- Production evaluation should preserve trace/correlation identifiers from B31.

## Current scope
The implementation is provider-neutral and deterministic when injected metrics/runners are deterministic. Dataset management, LLM-as-a-judge adapters, regression suites, statistical analysis, experiment tracking and CI gates are future extensions.


## B42 Feedback Integration

B42 consumes `EvaluationRun` objects from this framework through `ModelQualityIntelligence.ingest_run()`.

For best attribution, evaluation cases should include:

`provider`, `model`, `task`, and optionally `model_family` in `EvaluationCase.metadata`.

The learned result is exposed as a `QualitySignal` compatible with B41. Quality is bounded to [0,1], confidence is explicit, and missing model identity or metrics produces no quality signal.

B42 supports exact-model and family-level learning and optional durable profiles through its JSON profile store. It does not turn evaluation status alone into a quality score.

## Versioned run export and paired model benchmark

Use `core.evaluation.serialization.save_evaluation_run(run, path)` to persist an `EvaluationRun` as versioned JSON, and `load_evaluation_run(path)` to restore it for offline processing. The format preserves case attribution, metric evidence, outputs, errors, and duration; export requires JSON-compatible outputs and metadata.

The B32 route benchmark runner is `scripts/run_model_routing_benchmark.py`. It evaluates each enabled/healthy configured route independently against the same benchmark cases, saves actual results with explicit provider/model/task/group attribution, records per-case elapsed duration, and uses isolated in-memory health/usage stores to avoid mutating production telemetry. Calls still go to configured external providers and may incur charges.

For the B43 workflow, seed missing B42 profiles from a **prior** attributed evaluation with `scripts/ingest_model_quality.py`, then freeze normalized historical features with `scripts/build_routing_feature_snapshot.py`, before executing the target benchmark. The B43 proposal CLI enforces snapshot/profile timestamps to reduce feature leakage. See [B43 Benchmark Runbook](../models/B43_BENCHMARK_RUNBOOK.md). The proposal workflow does not synthesize missing evidence or activate policies.
