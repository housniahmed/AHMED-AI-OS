# B43 — Model Routing Learning & Policy Optimization

B43 learns routing-policy weights offline from paired benchmark results, then subjects proposed changes to statistical gates and human approval.

## Flow

`B32 EvaluationRun + B39/B40/B42 feature snapshot → paired samples → deterministic train/validation split → candidate weight search → uplift estimate → proposal → human approval → active revision`

## Building a paired dataset

Each relevant B32 result must include metadata:

- `provider`
- `model`
- `task`
- one shared benchmark group identifier: `benchmark_case_id`, `dataset_case_id`, or `evaluation_group_id`

Each group must include at least two evaluated provider/model candidates on the same benchmark case. The caller supplies a feature resolver:

```python
report = PolicyDatasetBuilder.from_evaluation_run(
    evaluation_run,
    feature_resolver=lambda provider, model, task: PolicyFeatureVector(
        reliability=...,
        latency=...,
        quality=...,
        cost=...,
    ),
)
```

Features are normalized [0,1]. In production, the resolver should use B39 health state, B40 latency/cost telemetry, and B42 evaluation-derived quality. B32 metric scores supply the outcome label; they are distinct from the B42 quality feature used by the policy.

## Optimization and evaluation

The optimizer creates a small deterministic set of weight candidates from reliability-, latency-, quality-, cost-focused and balanced recipes blended with the baseline policy. Candidate selection happens on the training split; uplift is measured on the held-out validation split.

A proposal is eligible only when all gates pass:

- minimum training count
- minimum validation count
- mean paired quality uplift at or above the configured threshold
- lower confidence bound above zero

The policy optimizer never auto-promotes a candidate. A good training score alone is insufficient.

## Approval and rollback

```python
optimizer = RoutingPolicyOptimizer(...)
proposal = optimizer.propose(ModelTask.REASONING, report.samples)

# A pending proposal remains inactive until a human explicitly approves it.
revision = optimizer.approve(
    proposal.id,
    approver="authorized-reviewer",
    expected_revision=proposal.baseline_revision,
    reason="Validated against held-out benchmark",
)

# Roll back by creating a new revision pointing at the previous policy.
rollback_revision = optimizer.rollback(
    ModelTask.REASONING,
    actor="authorized-reviewer",
    expected_revision=revision.revision,
    reason="Quality regression detected",
)
```

Approval requires a named actor, a reason, and the expected active revision. Stale proposals are rejected. The caller must authenticate and authorize the actor; the supplied actor string is audit attribution, not authentication. Revisions, proposal state, and audit events can be persisted with `JsonFilePolicyLifecycleStore`.

## Runtime integration

When `MODEL_ROUTING_MODE=adaptive`, the provider factory passes the optimizer to B41 as a policy source. B41 resolves the active policy per task. The default mode remains `priority`.

## Safety and operational boundaries

- Policy proposals are not active until explicit approval.
- Hard constraints in the policy remain intact; the optimizer only searches weight combinations.
- The B39 circuit breaker and fallback behavior remain in the router.
- B43 does not execute tools or change B17/B18/B33 permissions/governance.
- JSON persistence is single-process; use transactional storage with locking for multi-worker environments.

## Operational benchmark workflow

For live, paired measurements, configure at least two provider/model routes per task and run `scripts/run_model_routing_benchmark.py` against a version 1 dataset of real task prompts and deterministic scoring criteria. It tests each route independently rather than allowing the active adaptive policy to choose the winner. Requests go to configured external providers and may incur costs.

The runner saves actual outputs and attribution in the versioned B32 evaluation-run format. Then `scripts/propose_routing_policy.py` reads that run plus an explicit normalized B39/B40/B42 feature snapshot and persists proposals. The complete workflow and scoring schema are in [B43 Benchmark Runbook](B43_BENCHMARK_RUNBOOK.md).

B32 evaluation runs can be exported as versioned JSON with `save_evaluation_run(run, path)` from `core.evaluation.serialization`. From the repository root, the B43 CLI reads that real run plus an explicit normalized B39/B40/B42 feature snapshot and persists proposals:

```bash
python scripts/propose_routing_policy.py \
  --evaluation-run artifacts/evaluation-run.json \
  --features artifacts/routing-features.json \
  --store-path data/model-routing-policies.json
```

The CLI reports per-task sample counts, skipped evidence, held-out uplift, confidence bounds, gate status, and candidate weights. It never activates a candidate. See [B43 Benchmark Runbook](B43_BENCHMARK_RUNBOOK.md) for the input schema, normalized feature semantics, review steps, and limitations. Synthetic fixtures in the integration tests verify the workflow only; they are not real model benchmark evidence.
