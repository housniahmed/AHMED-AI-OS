# Unified Context / Personal Knowledge Fabric — Brique 11

Brique 11 creates the canonical representation consumed by higher-level agents. It unifies retrieval candidates, structured context and graph relationships into nodes and edges.

## Contract

`RETRIEVAL + CONTEXT + GRAPH -> KNOWLEDGE FABRIC -> AGENT`

The fabric preserves source identifiers, relevance, metadata and graph provenance. It is a context projection, not a second database: authoritative persistence remains in the underlying memory, knowledge and graph stores.

The builder is deterministic and bounded by a node budget. Future versions can add temporal reasoning, entity resolution, graph expansion and token-aware packing without changing the public fabric contract.
