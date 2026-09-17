# Memory Lifecycle & Learning Engine — Brique 9

Brique 9 defines how memory evolves after capture.

## Lifecycle

`CAPTURE -> VALIDATE -> CONSOLIDATE -> UPDATE -> DECAY -> ARCHIVE`

The implementation is deliberately conservative:

- memories require content and provenance;
- validity windows are checked explicitly;
- stale memories are flagged as decay candidates;
- exact duplicates are detected deterministically;
- no memory is silently deleted or overwritten;
- semantic similarity, contradiction detection and learned importance are deferred until the retrieval/embedding infrastructure is mature.

This is a lifecycle policy layer, not yet an autonomous learning system. Future iterations can add confidence updates, contradiction handling, semantic consolidation and user-approved forgetting.
