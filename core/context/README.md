# Context Engine

Brique 5 sits between retrieval and reasoning.

```text
USER QUERY
   ↓
RETRIEVAL
   ↓
CONTEXT ENGINE
   ├── relevance ordering
   ├── sensitivity enforcement
   ├── semantic classification
   ├── deduplication
   ├── character budget
   └── provenance preservation
   ↓
STRUCTURED CONTEXT
   ├── knowledge
   ├── memories
   ├── decisions
   ├── goals
   ├── projects
   └── procedures
   ↓
LLM / AGENT
```

## Design principles

1. Context is not a bag of retrieved chunks.
2. Security filtering happens before context assembly.
3. Provenance travels with every context item.
4. Semantic roles remain explicit so the model can distinguish facts, memories, decisions and procedures.
5. Duplicate content is removed deterministically.
6. The engine enforces a bounded character budget. Tokenizer-specific budgeting is intentionally deferred.

The current implementation is deterministic and provider-agnostic. The character budget and retrieval scoring defaults are engineering defaults, not experimentally optimized values.
