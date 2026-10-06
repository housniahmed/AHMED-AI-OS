# B42 — Model Quality Intelligence & Evaluation Feedback Loop

B42 turns B32 evaluation evidence into bounded, explicit quality intelligence consumed by B41.

## Flow

B32 Evaluation Case
→ explicit provider/model/task metadata
→ EvaluationResult
→ QualityFeedbackEngine
→ historical QualityObservation
→ QualityProfile
→ B41 QualitySignal

## Identity boundary

Evaluation cases must explicitly declare:

- provider
- model
- task

B42 never infers model identity from output text, provider success, latency, or cost.

## Quality profile

A profile contains:

- quality score in [0, 1]
- sample size
- pass rate
- trend versus the previous observation
- confidence based on evidence volume
- complete observation history

The score combines historical evidence with a configurable recency weight. This is an evaluation signal, not a probability that the model is truthful.

## Metric weighting

QualityFeedbackPolicy.metric_weights can weight evaluation metrics explicitly. If no weights are configured, metric scores are averaged.

## Feedback boundary

refresh_signal() can update a B41 QualitySignalStore explicitly. B42 does not autonomously rewrite routing policy weights and does not enable/disable providers.

## Governance

B42:

- does not execute tools
- does not approve actions
- does not change security permissions
- does not bypass B39 reliability constraints
- does not bypass B18 governance

B41 remains responsible for route arbitration; B42 only supplies quality evidence.

## Future evolution

A later brick may add statistically robust confidence intervals, evaluator drift detection, benchmark cohorts, and policy optimization. Those mechanisms should remain explicit and auditable.
