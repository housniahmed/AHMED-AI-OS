# B43 — Benchmark-to-policy proposal runbook

This runbook connects an actual B32 evaluation run to the B43 optimizer. It is an offline workflow; it does not invoke a model provider, invent observations, or activate the proposed policy.

## 1. Produce and export a B32 evaluation run

Use the existing B32 `EvaluationFramework` with the benchmark cases and runner for your actual provider/model candidates. Each `EvaluationCase.metadata` must explicitly include:

- `provider`: provider identity used for that run
- `model`: exact model identifier
- `task`: one of `chat`, `reasoning`, `extraction`, `classification`, `embedding`
- `benchmark_case_id`: a stable ID shared by all candidates evaluated against the same benchmark case

The metrics must score observed behavior and use explicit, documented definitions and thresholds. A passing request or HTTP response is not a quality score. Do not compare models using different benchmark cases under the same group ID.

Export the completed run from the application that executed the benchmark:

```python
from core.evaluation.serialization import save_evaluation_run

# evaluation_run is the real EvaluationRun returned by EvaluationFramework.run(...)
save_evaluation_run(evaluation_run, "artifacts/evaluation-run.json")
```

The JSON schema is versioned and preserves run IDs, case IDs, metrics, evaluation status, duration, output, errors, and attribution metadata. Exported outputs and metadata must be JSON-compatible.

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
