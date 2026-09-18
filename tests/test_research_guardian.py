from dataclasses import dataclass
from core.research.guardian import ResearchGuardian
from core.research.models import Claim, EvidenceStatus, Source, SourceVerification
from core.research.validators import ClaimMatcher, SourceResolver, SourceVerifier

@dataclass
class Resolver(SourceResolver):
    sources: tuple[Source, ...]
    def resolve(self, claim):
        return self.sources

class Verifier(SourceVerifier):
    def __init__(self, exists=True, metadata_valid=True):
        self.exists, self.metadata_valid = exists, metadata_valid
    def verify(self, source):
        return SourceVerification(source.id, self.exists, self.metadata_valid, "test-verifier")

class Matcher(ClaimMatcher):
    def __init__(self, scores):
        self.scores = scores
    def match(self, claim, source):
        return self.scores.get(source.id)

def make_guardian(source, score, **verification):
    return ResearchGuardian(Resolver((source,)), Verifier(**verification), Matcher({source.id: score}))

def test_supported_claim_preserves_provenance():
    source = Source(title="Verified paper", locator="doi:10.1234/example")
    assessment = make_guardian(source, 0.9).assess_claim(Claim("The claim"))
    assert assessment.status is EvidenceStatus.SUPPORTED
    assert assessment.matched_source_ids == (source.id,)
    assert assessment.provenance == ("test-verifier",)

def test_partial_claim():
    source = Source(title="Verified paper")
    assert make_guardian(source, 0.6).assess_claim(Claim("The claim")).status is EvidenceStatus.PARTIALLY_SUPPORTED

def test_unmatched_existing_source_is_unsupported():
    source = Source(title="Verified paper")
    assert make_guardian(source, 0.2).assess_claim(Claim("The claim")).status is EvidenceStatus.UNSUPPORTED

def test_unverified_source_requires_verification():
    source = Source(title="Candidate")
    assert make_guardian(source, 0.95, exists=None).assess_claim(Claim("The claim")).status is EvidenceStatus.REQUIRES_VERIFICATION

def test_empty_resolution_requires_verification():
    guardian = ResearchGuardian(Resolver(()), Verifier(), Matcher({}))
    assert guardian.assess_claim(Claim("The claim")).status is EvidenceStatus.REQUIRES_VERIFICATION

def test_report_counts():
    source = Source(title="Verified paper")
    report = make_guardian(source, 0.9).assess([Claim("A"), Claim("B")])
    assert report.counts[EvidenceStatus.SUPPORTED] == 2

def test_invalid_match_score_is_rejected():
    source = Source(title="Verified paper")
    try:
        make_guardian(source, 1.1).assess_claim(Claim("The claim"))
        assert False
    except ValueError:
        pass

def test_doi_format_validation():
    source = Source(title="Paper", doi="10.1234/abc")
    assert ResearchGuardian.validate_source_metadata(source)["doi_format_valid"] is True
