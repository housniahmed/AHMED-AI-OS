# B43 — Benchmark-to-policy proposal runbook

This runbook connects an actual B32 evaluation run to the B43 optimizer. It is an offline workflow; it does not invoke a model provider, invent observations, or activate the proposed policy.

## 1. Execute and export a paired B32 benchmark

First, prepare a dataset JSON file for the actual workflows you want to compare. The runner accepts a version 1 document with a `cases` array. Each case has a stable ID, task, prompt, scoring specification, and optional threshold. Example schema (replace this illustrative case with your own representative prompts and expected facts):

```json
{
  "schema_version": 1,
  "cases": [
    {
      "id": "reasoning-001",
      "name": "check a factual answer",
      "task": "reasoning",
      "input": "YOUR REAL BENCHMARK PROMPT",
      "expected": {
        "kind": "required_terms",
        "terms": ["EXPECTED FACT A", "EXPECTED FACT B"]
      },
      "threshold": 0.75
    }
  ]
}
```

The deterministic scorer supports `required_terms` (fraction of case-insensitive terms found), `exact_answer` (normalized exact match), and `json_fields` (fraction of expected JSON key/value pairs that match). These metrics are only appropriate when their definitions match the task; they are not a universal measure of model quality.

Configure at least two routes for every benchmark task using the existing `MODEL_PROVIDER_*` or `MODEL_PROVIDER_IDS` environment settings, then run:

```bash
python scripts/run_model_routing_benchmark.py \
  --dataset evals/my-benchmark.json \
  --output artifacts/evaluation-run.json \
  --limit-per-task 10
```

The default limit of 10 paired cases per task is a cost-conscious smoke run, not enough for default B43 promotion gates. With the current 20% deterministic validation split, plan roughly 100 paired cases per task to yield at least 20 validation samples and 20 training samples; use `--limit-per-task 100` only after preparing that dataset and confirming the expected provider cost. Every selected case is sent to each configured candidate route for its task. The runner saves actual outputs and attribution to the versioned B32 run format. Do not commit sensitive prompts or raw provider outputs to the repository.

The runner creates a B32 result per candidate/case pair and records these required attribution fields in each result: `provider`, `model`, `task`, and the shared `benchmark_case_id`. Metrics score observed behavior using the scoring criterion you declare for each case. A passing request or HTTP response is not a quality score, and different prompts must not share a group ID unless they represent the same evaluation case.

To export a run produced through the B32 API instead of the CLI, use:

```python
from core.evaluation.serialization import save_evaluation_run

save_evaluation_run(evaluation_run, "artifacts/evaluation-run.json")
```

The versioned JSON schema preserves run IDs, case IDs, metrics, evaluation status, duration, output, errors, and attribution metadata. Outputs and metadata must be JSON-compatible. Do not commit sensitive prompts or raw provider outputs to the repository.

## 2. Prepare the feature snapshot

Create a JSON file named, for example, `artifacts/routing-features.json`:

```json
{
  "schema_version": 1,
  "features": [
    {
      "provider": "REPLACE_WITH_OBSERVED_PROVIDER",
      "model": "REPLACE_WITH_OBSERVED_MODEL",
      "task": "reasoning",
      "reliability": 0.0,
      "latency": 0.0,
      "quality": 0.0,
      "cost": 0.0,
      "priority": 0
    }
  ]
}
```

The zero values above are schema placeholders, not benchmark measurements. Replace them with a snapshot derived from the actual B39/B40/B42 evidence before running an analysis. Include one row per exact provider/model/task identity represented in the evaluation run.

All four features must be numeric and normalized to `[0, 1]`, with **higher meaning better**:
- `reliability`: reliability estimate derived from B39 observations
- `latency`: normalized latency/speed score derived from B40 latency observations (not raw milliseconds)
- `quality`: confidence-aware quality score derived from B42 or another documented evaluator
- `cost`: normalized cost-efficiency score derived from configured B40 pricing (not raw USD)

Do not fill missing evidence with estimates that look observed. Missing feature rows are skipped, and unpaired groups cannot be used by the optimizer.

## 3. Build proposals

From the repository root, run:

```bash
python scripts/propose_routing_policy.py \
  --evaluation-run artifacts/evaluation-run.json \
  --features artifacts/routing-features.json \
  --store-path data/model-routing-policies.json
```

The command builds paired samples, reports skipped rows/groups and reasons, splits samples deterministically into training and held-out validation subsets, and persists one proposal per task with usable paired data. The dataset ID defaults to a SHA-256 fingerprint of both input files. The store also records the baseline revision, proposal state, and audit events.

Defaults are 20 training samples, 20 validation samples, mean held-out uplift of at least 0.02, and a 1.96 confidence multiplier. For an exploratory run, thresholds can be changed with CLI flags; any relaxed thresholds must be justified in the evaluation plan and must not be used to misrepresent weak evidence as production-ready.

A proposal can have status `insufficient_evidence` even when the command succeeds. This is expected when sample counts, uplift, or confidence gates are not met. Exit code `2` means invalid input or that no usable proposal could be created.

## 4. Review before activation

Review the CLI report and the persisted proposal:
- verify attribution, sample counts, skipped reasons, feature freshness, metric semantics, uplift, and confidence lower bound;
- inspect the active baseline and candidate weight differences;
- repeat on an independent benchmark if the evaluation plan requires it;
- have an authenticated and authorized reviewer approve the proposal through the application's governance boundary using its current expected revision.

The CLI intentionally never calls `approve()`; it reports `"activation_performed": false`. The JSON lifecycle store is single-process and is not safe for concurrent multi-worker approval workflows. Use a transactional store with revision checks for that deployment shape.

## 5. Validation boundary

The CLI tests use synthetic data only as test fixtures to test wiring and the non-activation invariant. They are not empirical model benchmarks and must never be used as evidence that one real model is better than another.

The command does not automatically read live provider health, usage, pricing, or quality stores. The feature snapshot is an explicit input so that each proposal can be tied to a reproducible snapshot. Automatic snapshot collection is a separate integration task.
