"""Domain models for the knowledge ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class Document:
    """A source document registered in the knowledge base."""

    name: str
    source_type: str
    source_uri: str
    id: UUID = field(default_factory=uuid4)
    mime_type: str | None = None
    checksum_sha256: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class DocumentChunk:
    """A retrievable unit that retains exact document provenance."""

    document_id: UUID
    content: str
    chunk_index: int
    id: UUID = field(default_factory=uuid4)
    page: int | None = None
    section: str | None = None
    char_start: int | None = None
    char_end: int | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
