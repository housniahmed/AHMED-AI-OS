# B20 — Advanced RAG

Advanced RAG is a provider-neutral retrieval pipeline above the existing hybrid retrieval engine.

Flow:
QUERY -> OPTIONAL EXPANSION -> HYBRID RETRIEVAL -> DEDUPLICATION -> OPTIONAL RERANKING -> CONTEXT COMPRESSION -> CITATIONS -> GROUNDING SIGNAL

The pipeline supports injected query expansion, reranking and context compression providers. No LLM or vector database SDK is embedded in the core.

Safety:
- retrieval continues to enforce sensitivity filtering;
- project scope is forwarded to retrieval;
- duplicate passages are removed by stable candidate id;
- context has an explicit character budget;
- provenance is retained as citations;
- grounding_score is a retrieval-support signal, not a factuality guarantee.

The current grounding score is the mean fused retrieval score of selected passages. It must not be interpreted as a probability of answer correctness.

Future extensions: embedding-backed dense retrieval, cross-encoder reranking, semantic query expansion, parent-document retrieval, metadata filters, contextual compression and answer-level citation validation.
