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
