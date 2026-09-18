"""Research Guardian: source-grounded evidence assessment."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from .models import Claim, EvidenceStatus, ResearchAssessment, ResearchReport, Source, SourceVerification
from .validators import ClaimMatcher, SourceResolver, SourceVerifier, validate_doi_format

@dataclass(frozen=True, slots=True)
class GuardianConfig:
    partial_match_threshold: float = 0.50
    supported_match_threshold: float = 0.80
    def __post_init__(self) -> None:
        if not 0.0 <= self.partial_match_threshold <= self.supported_match_threshold <= 1.0:
            raise ValueError("thresholds must satisfy 0 <= partial <= supported <= 1")

class ResearchGuardian:
    def __init__(self, resolver: SourceResolver, verifier: SourceVerifier, matcher: ClaimMatcher, config: GuardianConfig | None = None) -> None:
        self.resolver, self.verifier, self.matcher = resolver, verifier, matcher
        self.config = config or GuardianConfig()

    def assess_claim(self, claim: Claim) -> ResearchAssessment:
        candidates = tuple(self.resolver.resolve(claim))
        if not candidates:
            return ResearchAssessment(claim.id, EvidenceStatus.REQUIRES_VERIFICATION, "No candidate source was resolved; evidence cannot be established.")
        matched: list[Source] = []
        verifications: list[SourceVerification] = []
        best_score: float | None = None
        provenance: list[str] = []
        for source in candidates:
            verification = self.verifier.verify(source)
            verifications.append(verification)
            provenance.append(verification.provenance)
            if verification.exists is not True or verification.metadata_valid is False:
                continue
            score = self.matcher.match(claim, source)
            if score is None:
                continue
            if not 0.0 <= score <= 1.0:
                raise ValueError("claim match score must be between 0 and 1")
            best_score = score if best_score is None else max(best_score, score)
            if score >= self.config.partial_match_threshold:
                matched.append(source)
        if not matched:
            status = EvidenceStatus.UNSUPPORTED if verifications and all(v.exists is True for v in verifications) else EvidenceStatus.REQUIRES_VERIFICATION
            rationale = "No verified source sufficiently matches the claim."
        elif best_score is not None and best_score >= self.config.supported_match_threshold:
            status, rationale = EvidenceStatus.SUPPORTED, "At least one verified source meets the configured support threshold."
        else:
            status, rationale = EvidenceStatus.PARTIALLY_SUPPORTED, "Verified source evidence reaches the partial-support threshold but not the support threshold."
        return ResearchAssessment(claim.id, status, rationale, tuple(s.id for s in matched), tuple(v.source_id for v in verifications), tuple(dict.fromkeys(provenance)), best_score)

    def assess(self, claims: Iterable[Claim]) -> ResearchReport:
        return ResearchReport(tuple(self.assess_claim(claim) for claim in claims))

    @staticmethod
    def validate_source_metadata(source: Source) -> dict[str, bool | None]:
        return {"doi_format_valid": validate_doi_format(source.doi), "title_present": bool(source.title.strip()), "locator_present": bool(source.locator and source.locator.strip())}
