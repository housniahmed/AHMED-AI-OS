"""Domain models for source-grounded research verification."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class EvidenceStatus(str, Enum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"
    REQUIRES_VERIFICATION = "requires_verification"

@dataclass(frozen=True, slots=True)
class Claim:
    text: str
    id: UUID = field(default_factory=uuid4)
    source_locator: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class Source:
    title: str
    id: UUID = field(default_factory=uuid4)
    source_type: str = "unknown"
    locator: str | None = None
    authors: tuple[str, ...] = ()
    doi: str | None = None
    publication_year: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class SourceVerification:
    source_id: UUID
    exists: bool | None
    metadata_valid: bool | None
    provenance: str
    checked_at: datetime = field(default_factory=utc_now)
    details: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class ResearchAssessment:
    claim_id: UUID
    status: EvidenceStatus
    rationale: str
    matched_source_ids: tuple[UUID, ...] = ()
    verification_ids: tuple[UUID, ...] = ()
    provenance: tuple[str, ...] = ()
    confidence: float | None = None

@dataclass(frozen=True, slots=True)
class ResearchReport:
    assessments: tuple[ResearchAssessment, ...]
    generated_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)
    @property
    def counts(self) -> dict[EvidenceStatus, int]:
        result = {status: 0 for status in EvidenceStatus}
        for item in self.assessments:
            result[item.status] += 1
        return result
