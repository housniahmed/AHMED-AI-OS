# Knowledge Graph — Brique 10

Brique 10 adds an entity-and-relationship layer above memory and documents.

## Model

`ENTITY <-> RELATIONSHIP <-> ENTITY`

Entities have stable IDs, types, names, aliases and metadata. Relationships have typed predicates, optional confidence and provenance. The graph is intentionally provider-neutral; the current reference implementation is in-memory and can later be backed by PostgreSQL, a graph database, or another storage engine.

## Why this layer exists

Retrieval answers: "which pieces of information are relevant?"

The graph answers: "how are these pieces connected?"

This enables future context expansion such as project -> goal -> document -> concept, while keeping provenance and confidence explicit.

## Safety

Relationships cannot be created unless both endpoints already exist. No inferred relationship is silently treated as fact; inferred edges should carry provenance and confidence.
