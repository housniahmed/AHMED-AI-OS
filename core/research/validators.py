"""Validation contracts and deterministic source checks."""
from __future__ import annotations
from abc import ABC, abstractmethod
import re
from typing import Iterable
from .models import Claim, Source, SourceVerification

DOI_PATTERN = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$", re.I)

class SourceResolver(ABC):
    @abstractmethod
    def resolve(self, claim: Claim) -> Iterable[Source]:
        raise NotImplementedError

class SourceVerifier(ABC):
    @abstractmethod
    def verify(self, source: Source) -> SourceVerification:
        raise NotImplementedError

class ClaimMatcher(ABC):
    @abstractmethod
    def match(self, claim: Claim, source: Source) -> float | None:
        raise NotImplementedError

def validate_doi_format(doi: str | None) -> bool | None:
    if doi is None:
        return None
    normalized = doi.removeprefix("https://doi.org/").removeprefix("http://doi.org/").strip()
    return bool(DOI_PATTERN.fullmatch(normalized))
