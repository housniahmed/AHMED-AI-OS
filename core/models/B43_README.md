# B43 — Model Routing Learning & Policy Optimization

B43 learns routing-policy weights offline from paired benchmark results. It makes proposals, not autonomous policy changes.

## Evidence flow

`historical B39/B40/B42 snapshot → paired B32 benchmark → train/validation split → candidate weight search → uplift and confidence gates → proposal → explicit human approval → policy revision`

Every evaluation result must contain explicit `provider`, `model`, `task`, metric scores, and one shared benchmark group identifier (`benchmark_case_id`, `dataset_case_id`, or `evaluation_group_id`). Each group must contain at least two candidate models evaluated on the same benchmark case. Missing evidence is skipped, never fabricated.

## 1. Freeze historical features before the benchmark

Build a feature snapshot from observed B40 attempt telemetry and exact B42 quality profiles, optionally using current B39 provider health to exclude disabled/open-circuit providers:

```bash
python scripts/build_routing_feature_snapshot.py \
  --usage-store data/model-usage.json \
  --quality-store data/model-quality.json \
  --health-store data/model-health.json \
  --output artifacts/routing-features.json
```

Only pass `--health-store` when that actual B39 file exists. The collector skips candidates with insufficient attempts, incomplete pricing, missing exact quality profiles, or unusable evidence; inspect its output diagnostics. Scores are normalized [0,1], higher-is-better. Reliability is observed successful attempts / all attempts. Latency and cost use explicit scales, and B42 quality is blended with the declared prior according to profile confidence.

The snapshot and every exact B42 quality observation must predate the benchmark run. The B43 proposal CLI enforces the snapshot timestamp and B42 evidence timestamp against the B32 run start time to reduce evaluation leakage. Create and freeze the snapshot first; do not regenerate it after the run to evaluate that same run.

## 2. Run a paired B32 benchmark

Create a version 1 dataset JSON with real representative prompts, stable case IDs, and task-appropriate deterministic scoring criteria. The benchmark runner supports `required_terms`, `exact_answer`, and `json_fields`; these simple criteria are not universal quality measures.

Configure at least two routes per task, then run:

```bash
python scripts/run_model_routing_benchmark.py \
  --dataset evals/my-benchmark.json \
  --output artifacts/evaluation-run.json \
  --limit-per-task 10
```

The default limit of 10 is a cost-conscious smoke run and usually does not satisfy promotion gates. Each case is submitted to each configured candidate route; requests can incur provider charges. The runner scores candidates separately instead of allowing adaptive arbitration to choose one, and saves actual results in the versioned B32 JSON format.

## 3. Propose a routing policy

Use the frozen feature snapshot from step 1:

```bash
python scripts/propose_routing_policy.py \
  --evaluation-run artifacts/evaluation-run.json \
  --features artifacts/routing-features.json \
  --store-path data/model-routing-policies.json
```

The command builds paired samples, records skipped evidence, applies the deterministic train/validation split, compares candidate weights on training data, and reports held-out uplift and confidence bounds. The dataset ID defaults to a SHA-256 fingerprint of the evaluation-run and feature files.

Default gates require at least 20 training samples, 20 validation samples, mean held-out uplift of at least 0.02, and a 1.96 confidence multiplier. A proposal may stay `insufficient_evidence` when any gate fails. The CLI reports `"activation_performed": false` and never calls `approve()`.

## Approval, revisions and rollback

```python
proposal = optimizer.propose(ModelTask.REASONING, report.samples)
revision = optimizer.approve(
    proposal.id,
    approver="authorized-reviewer",
    expected_revision=proposal.baseline_revision,
    reason="Held-out benchmark reviewed",
)
rollback_revision = optimizer.rollback(
    ModelTask.REASONING,
    actor="authorized-reviewer",
    expected_revision=revision.revision,
    reason="Regression detected",
)
```

The caller must authenticate and authorize the approver; the actor string itself is audit attribution, not authentication. Revision checks block stale promotion. Rollback creates a new revision pointing at the previous policy. The JSON store is single-process; multi-worker deployments need transactional persistence with locking or compare-and-swap.

## Runtime and governance boundaries

When `MODEL_ROUTING_MODE=adaptive`, B41 resolves the active task-specific B43 policy. Priority mode remains the default. The optimizer changes weights only; it does not bypass route hard constraints, B39 circuit breakers, tool permissions, B18 approvals, or B33 security controls.

The benchmark runner and automated tests do not establish which real model is best until the workflow is run against configured external providers and a representative user-maintained dataset. Test fixtures use mock providers solely to verify wiring and non-activation behavior.
