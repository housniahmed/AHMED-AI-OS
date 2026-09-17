"""Document ingestion orchestration.

The service converts a source into a document record and provenance-aware
chunks. Embeddings are deliberately a later stage.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from core.knowledge.chunking import chunk_text
from core.knowledge.models import Document, DocumentChunk
from core.knowledge.parsers import parse_source


class IngestionService:
    def ingest_file(
        self,
        path: str | Path,
        *,
        chunk_size: int = 1200,
        overlap: int = 200,
        metadata: dict[str, str] | None = None,
    ) -> tuple[Document, list[DocumentChunk]]:
        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError(source)

        content = parse_source(source)
        checksum = hashlib.sha256(source.read_bytes()).hexdigest()
        document = Document(
            name=source.name,
            source_type="filesystem",
            source_uri=str(source.resolve()),
            mime_type=None,
            checksum_sha256=checksum,
            metadata=metadata or {},
        )

        chunks = [
            DocumentChunk(
                document_id=document.id,
                content=chunk.content,
                chunk_index=index,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
            )
            for index, chunk in enumerate(
                chunk_text(content, chunk_size=chunk_size, overlap=overlap)
            )
        ]
        return document, chunks
