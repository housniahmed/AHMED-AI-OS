# B34 — Deployment

B34 defines the deployment boundary for AHMED AI OS.

## Local container deployment

`docker compose up --build` starts the API and PostgreSQL services. The API exposes port 8000 and the database uses a named Docker volume.

## Production principles
- Secrets are supplied through the environment or an external secret manager; never commit `.env`.
- Use TLS at the ingress/reverse-proxy layer.
- Add authentication/authorization from B33 before public exposure.
- Use durable PostgreSQL persistence instead of the API's current in-memory bootstrap services.
- Add health/readiness checks, backups, migrations, resource limits and restart policies before production.
- Pin and regularly update container dependencies/images.
- Add B31 telemetry and centralized logs.
- Run B32 regression/evaluation suites in CI before release.
- Do not treat a successful container build as proof of production readiness.

## Current scope
The repository now contains a reproducible container baseline and Compose topology. It is not a claim that the full application is production-ready: API authentication, durable service wiring, migrations, TLS, observability exporters, CI/CD and infrastructure hardening remain deployment work.
