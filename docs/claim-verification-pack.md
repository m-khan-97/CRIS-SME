# Claim Verification Pack

The Claim Verification Pack turns stakeholder-facing CRIS-SME statements into verifiable claim objects.

It answers:

- what exact claim is being made?
- who is the audience?
- which report sections support it?
- which controls, findings, evidence references, provenance nodes, and RBOM artifacts back it?
- is the claim verified, caveated, or unverified?
- does the claim affect deterministic risk scoring?

## Claim Types

Current claim types include:

- `overall_risk`
- `top_risk`
- `cyber_essentials_readiness`
- `cyber_essentials_pillar`
- `insurance_question`
- `replay`
- `integrity`
- `trust_badge`

## Report Output

CRIS-SME writes:

`outputs/reports/cris_sme_claim_verification_pack.json`

Reports also include:

`claim_verification_pack`

The dashboard payload includes:

`claim_verification_pack`

The RBOM includes the claim pack as a hashed artifact.

## Boundary

Claim verification never changes deterministic CRIS-SME scores.

It verifies and caveats statements after scoring, reporting, replay, assurance, provenance, and RBOM generation.

## Why This Matters

Most security reports include claims that are hard to trace.

CRIS-SME claim packs make executive, compliance, and insurance statements auditable instead of merely presentational.
