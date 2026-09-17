# Knowledge ingestion

## Current pipeline

```text
source file
    -> parser
    -> normalized text
    -> deterministic chunker
    -> provenance-aware DocumentChunk
```

The current milestone supports UTF-8 text-like formats: TXT, Markdown, reStructuredText, CSV and JSON.

Each chunk retains:

- document ID
- chunk index
- character start/end offsets
- creation timestamp

The parent document retains its SHA-256 checksum and source URI.

## Why embeddings are not here yet

The ingestion layer must be independently testable before a model-dependent embedding stage is introduced. This keeps parsing/chunking failures distinguishable from retrieval-model failures and makes re-indexing deterministic.

## Planned adapters

- PDF: page-aware parser
- DOCX: paragraph/table-aware parser
- HTML: content extraction with URL provenance
- Email: message/thread-aware parser

Those adapters will be added only with explicit provenance fields appropriate to each format; no parser should silently discard source location information.
