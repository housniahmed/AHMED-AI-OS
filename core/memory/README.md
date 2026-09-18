# Memory Layer — B1 / B9 / B19

## B19 — Advanced Memory

B19 adds deterministic recall and maintenance above the existing memory repository and lifecycle.

Flow:

CAPTURE -> VALIDATE -> STORE -> RECALL -> RANK -> CONSOLIDATE / DECAY / ARCHIVE

Recall combines four explicit signals:
- lexical relevance: 35%
- recency: 25%
- confidence: 20%
- explicit importance metadata: 20%

These are engineering defaults, not experimentally optimized weights.

## Safety

- Sensitivity is filtered before recall results are returned.
- Expired memories are excluded from recall.
- No memory is automatically deleted.
- Exact duplicates are reported, not silently removed.
- Contradictions are not inferred from text.
- Importance is read only from explicit metadata["importance"]; it is never guessed.

Embeddings, semantic similarity, contradiction detection, vector databases and learned importance remain injectable future capabilities.
