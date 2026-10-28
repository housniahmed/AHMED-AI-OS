# Evaluation datasets

## Model-routing smoke dataset

`model-routing-smoke.json` is a small, deterministic smoke dataset for checking the B32 paired model-runner wiring against two or more configured model routes. It covers exact-output instruction following, simple arithmetic, required terms, and JSON field extraction.

It is intentionally **not** a production model-quality benchmark:
- six cases are too few to meet B43's default training and validation sample gates;
- expected-value checks measure only the declared criterion, not general reasoning or truthfulness;
- provider outputs can vary and will affect score and pass rate;
- it should be used to validate configuration and estimate per-request latency/cost before assembling a representative benchmark.

## Run a smoke benchmark

From the repository root after installing the project and configuring provider credentials and at least two routes for the `reasoning` task:

```bash
python scripts/run_model_routing_benchmark.py \
  --dataset evals/model-routing-smoke.json \
  --output artifacts/model-routing-smoke-run.json \
  --limit-per-task 6
```

This invokes the configured external model endpoints and may incur charges. The runner isolates health and usage state in memory so this test does not update production B39/B40 telemetry. Save the output locally; evaluation outputs may contain sensitive text.

For B43 policy optimization, build an actual representative dataset with stable case IDs, justified scoring rules, and enough paired cases to pass the statistical gates. Generate the historical feature snapshot before the target benchmark, then pass the saved B32 run and frozen snapshot to `scripts/propose_routing_policy.py`. The proposal CLI never activates a candidate.
