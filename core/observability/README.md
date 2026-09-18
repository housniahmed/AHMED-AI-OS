# B31 — Observability

B31 establishes the observability boundary for AHMED AI OS.

## Signals
- Distributed trace context: trace_id, span_id, parent_span_id.
- Structured events across API, orchestration, agents, tools, workflows, memory and retrieval.
- Metrics as named numeric points with labels.
- Correlation with user_id and correlation_id where available.
- Explicit success/failure and duration fields.

## Invariants
- Observability records what happened; it does not authorize execution.
- Observability must not change business or orchestration decisions.
- No provider-specific telemetry SDK is required in core/observability.
- Sensitive payloads should not be placed in attributes; callers should emit identifiers and safe metadata instead.
- Trace IDs are correlation identifiers, not authentication credentials.
- Metrics are measurements, not evaluation judgments.

## Current scope
The implementation is an in-memory, injectable sink for deterministic tests and local development. OpenTelemetry/OTLP exporters, Prometheus, durable storage, dashboards, retention and production alerting are deferred to later hardening.
