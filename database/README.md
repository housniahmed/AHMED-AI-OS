# Database layer

The first persistence schema uses PostgreSQL as the system of record.

## Principles

- Relational data remains queryable with SQL.
- JSONB is used for flexible user-context metadata, not as a replacement for relational modeling.
- Every durable memory keeps explicit provenance (`source_type`, `source_id`, locator and optional excerpt).
- Sensitivity is stored with each memory so authorization can be enforced before retrieval.
- `pgvector` is intentionally not required by the first schema migration. Embeddings will be added after the deterministic persistence layer is validated.

## Planned evolution

1. PostgreSQL persistence
2. Repository integration tests
3. pgvector extension and embedding table
4. Hybrid retrieval (metadata + lexical + semantic)
5. Reranking and context assembly


## Brique 14 — Persistence scope

The schema now persists the planning hierarchy introduced by Brique 13:
Goals, Projects, project-goal links, Milestones, Tasks and task dependencies.
Temporal Events are also persisted as canonical time objects.

Foreign keys and CHECK constraints enforce structural invariants at the database
boundary. Application services remain responsible for domain-level transition
rules such as dependency completion before starting a task.

The PostgreSQL schema is the system of record; in-memory engines remain useful
for deterministic unit tests.
