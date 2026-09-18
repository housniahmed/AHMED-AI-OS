# B28 — AI OS API

B28 is the HTTP boundary of AHMED AI OS. It exposes stable API contracts while keeping domain logic in core and external provider credentials outside the API layer.

## Current endpoints

- GET /health
- POST /v1/users
- GET /v1/users/{user_id}/context
- PATCH /v1/users/{user_id}/profile
- GET /v1/business/snapshot

FastAPI provides OpenAPI documentation at /docs and /redoc when running.

## Boundary rules

HTTP/Pydantic concerns stay in apps/api. Business and identity rules stay in core. No provider SDK or credential is stored in this module. External writes must still pass through the existing gateway and governance controls.

The current process uses in-memory service instances as a bootstrap only. Authentication, authorization middleware, durable API persistence, rate limiting, audit logging, observability and deployment hardening belong to later bricks.

## Run locally

Install project dependencies, then run: uvicorn apps.api.main:app --reload
