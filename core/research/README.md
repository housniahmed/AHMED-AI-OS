# B21 — Research Guardian

Research Guardian is the evidence-verification layer of AHMED AI OS. It evaluates whether claims are supported by resolved and verified sources while preserving provenance.

## Pipeline
CLAIMS -> SOURCE RESOLUTION -> SOURCE VERIFICATION -> CLAIM/SOURCE MATCHING -> EVIDENCE STATUS -> REPORT

## Evidence statuses
- SUPPORTED: a verified source reaches the configured support threshold.
- PARTIALLY_SUPPORTED: verified evidence reaches the partial threshold but not the support threshold.
- UNSUPPORTED: candidate sources exist, but none sufficiently match the claim.
- REQUIRES_VERIFICATION: resolution, source existence, metadata, or matching is insufficient to establish support.

## Design invariants
1. No network provider is embedded in the core.
2. No source, DOI, author, title, result, statistic, or bibliographic field is fabricated.
3. An unverified source is not treated as evidence.
4. Provenance is retained on every assessment.
5. A match score is a matching signal, not a probability that the claim is true.
6. Thresholds are engineering defaults, not scientific validation results.

## Provider contracts
SourceResolver, SourceVerifier, and ClaimMatcher are dependency-injection ports. Future adapters may connect Crossref, OpenAlex, publisher APIs, institutional repositories, or approved databases without changing the Guardian core.

## DOI handling
The core performs DOI format validation only. DOI existence/resolution must be established by an injected verifier; a syntactically valid DOI is not proof that it exists or supports a claim.
