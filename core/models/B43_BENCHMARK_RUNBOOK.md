# B43 — Benchmark-to-policy runbook

This runbook connects historical B39/B40/B42 evidence to a real paired B32 evaluation run, then creates an auditable B43 proposal. It does not activate policies.

## 1. Freeze historical routing features first

The feature snapshot **must be generated before the benchmark run starts**. This keeps runtime evidence and B42 quality profiles independent of the outcomes being evaluated. The B43 proposal CLI enforces this using the snapshot timestamp, evaluation-run timestamp, and each exact B42 profile timestamp.

First, make sure B40 usage telemetry exists for the models you want to compare, B42 has exact provider/model/task quality profiles based on prior evaluations, and pricing is configured for the relevant routes. Missing pricing or quality evidence is not replaced with a made-up value.

From the repository root, generate a normalized snapshot:

```bash
python scripts/build_routing_feature_snapshot.py \
  --usage-store data/model-usage.json \
  --quality-store data/model-quality.json \
  --health-store data/model-health.json \
  --output artifacts/routing-features.json
```

Pass `--health-store` only when that B39 JSON file exists and contains the actual provider health state. The collector uses B40 observations for exact provider/model/task attempt reliability, latency, and estimated cost; it reads B42 exact-model quality profiles; and it excludes disabled or circuit-open providers when that state is available.

By default, it requires at least three usage attempts and one B42 quality observation, and it requires every usage attempt for a model/task to have configured pricing. It computes higher-is-better normalized scores using explicit scales: latency score `1 / (1 + mean_latency_ms / 1000)`, cost score `1 / (1 + mean_estimated_cost_usd / 0.01)`, and confidence-blended B42 quality with prior 0.5. Adjust scales only when the routing policy's corresponding scales are changed or the experiment plan justifies the difference.

The snapshot includes per-model evidence counts, cost/latency telemetry, B42 confidence and observation timestamp, skipped combinations/reasons, and a generation timestamp. If no valid features can be built, the collector writes diagnostics and exits with code 2. Check that at least two candidate model/task entries remain for each task in your intended benchmark.

**Do not run this snapshot step after the benchmark and then use those features for the same evaluation run.** B42 profiles updated from the benchmark itself would leak outcomes into the feature set, and later B40 usage could reflect the evaluation calls.

## 2. Prepare a representative benchmark dataset

Create a version 1 JSON file such as `evals/my-benchmark.json`. Each case requires a stable ID, name, task, prompt, expected result specification, and optional threshold:

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

The deterministic scorer supports three expectation kinds:
- `required_terms`: fraction of declared terms found, case-insensitively;
- `exact_answer`: normalized exact text match;
- `json_fields`: fraction of expected JSON key/value pairs found in the generated JSON object.

Use a scoring method that actually matches the task. These simple metrics are not universal measures of model quality. Populate the dataset with real representative tasks and correct expected results; do not copy the illustrative placeholders as empirical evidence.

## 3. Execute a paired B32 benchmark

Configure at least two provider/model routes for each task in your dataset using the existing `MODEL_PROVIDER_*` or `MODEL_PROVIDER_IDS` environment settings. Set API credentials through environment variables, not committed files. Then run:

```bash
python scripts/run_model_routing_benchmark.py \
  --dataset evals/my-benchmark.json \
  --output artifacts/evaluation-run.json \
  --limit-per-task 10
```

The default limit of 10 is a low-cost smoke run and normally does not satisfy B43 promotion gates. The default optimizer requires at least 20 training and 20 validation samples. Because the split is a stable hash-based 20% validation split, plan roughly 120 paired benchmark cases per task to give the validation set a buffer, then inspect the reported counts before considering a proposal. Each case is submitted once to each configured route for its task; provider retries may create additional billable attempts. Confirm your providers' current pricing before increasing the limit.

The runner evaluates each candidate route independently instead of letting adaptive arbitration choose a winner. The resulting B32 run contains actual output and metrics with explicit `provider`, `model`, `task`, and shared `benchmark_case_id` attribution. The run is saved in a versioned JSON format by `core.evaluation.serialization.save_evaluation_run`.

Do not commit sensitive prompts or raw provider outputs to the repository. The collector's feature snapshot must have been generated before this run; the proposal CLI rejects feature snapshots or quality observations dated on or after the run start.

## 4. Generate B43 proposals

Use the same frozen snapshot generated in step 1:

```bash
python scripts/propose_routing_policy.py \
  --evaluation-run artifacts/evaluation-run.json \
  --features artifacts/routing-features.json \
  --store-path data/model-routing-policies.json
```

The command builds paired samples, reports skipped results/groups and reasons, deterministically separates training and held-out validation cases, and writes one proposal per task with usable paired data. The dataset ID defaults to a SHA-256 fingerprint of the evaluation-run and feature files.

Default statistical gates are 20 training samples, 20 validation samples, mean held-out uplift of at least 0.02, and a 1.96 confidence multiplier. A proposal may correctly remain `insufficient_evidence` when sample counts, uplift, or confidence gates do not pass. Exit code 2 means invalid input or no usable paired data; inspect the diagnostic output and skipped reasons.

## 5. Review; never auto-promote

Review attribution, sample counts, skipped evidence, feature freshness, metric definitions, baseline/candidate scores, mean uplift, confidence lower bound, and candidate weights. Use independent validation if the experiment plan requires it. An authenticated and authorized human must approve an eligible proposal through the application's governance boundary with the current expected revision and a recorded reason.

The CLI deliberately never calls `approve()` and reports `"activation_performed": false`. The JSON policy store is for one process; use a transactional store with locking or compare-and-swap for multi-worker deployments.

The B32 runner and integration tests do not create evidence about which real model is best until you run them against configured external providers and your own benchmark. Test fixtures use mock providers solely to verify wiring and the non-activation invariant.
