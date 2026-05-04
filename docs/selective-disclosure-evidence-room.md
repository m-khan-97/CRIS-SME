# Selective Disclosure Evidence Room

CRIS-SME now produces a controlled evidence-sharing package for stakeholders who need assurance without raw cloud exposure.

## Disclosure Profiles

- `executive`: summary claims, trust badge, replay, RBOM, and high-level assurance case
- `customer`: customer due-diligence view with redacted top-risk evidence
- `insurer`: insurance-readiness view focused on claims, caveats, and mapped control evidence
- `auditor`: detailed redacted assurance evidence with provenance and withheld-evidence register
- `technical_appendix`: maximum redacted detail for technical review

## Outputs

CRIS-SME writes:

`outputs/reports/cris_sme_selective_disclosure.json`

`outputs/reports/cris_sme_evidence_room.html`

The static site bundle includes:

`dist/site/evidence-room.html`

`dist/site/data/cris_sme_selective_disclosure.json`

## Redaction Model

The package redacts sensitive tenant, subscription, resource, identity, email, IP, and resource-path values.

It preserves:

- control IDs
- finding IDs
- claim IDs
- verification status
- confidence
- evidence sufficiency
- proof strength
- caveats
- RBOM hash reference

## Withheld Evidence

When a profile cannot see raw or detailed evidence, the Evidence Room records:

- source section
- withholding reason
- replacement summary
- item identifier

This means CRIS-SME can share defensible assurance without pretending that sensitive evidence was never present.

## Boundary

Selective disclosure does not introduce new findings, claims, or scores.

It is a controlled presentation layer over existing deterministic CRIS-SME artifacts.
