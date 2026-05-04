# Report Trust Badge

The Report Trust Badge is a compact stakeholder-facing label for a CRIS-SME report.

It summarizes report assurance signals:

- deterministic replay
- Risk Bill of Materials presence
- provider contract conformance
- high-priority evidence gaps
- assessment assurance score

## Boundary

The badge never changes deterministic CRIS-SME risk scores.

It is a report trust indicator, not a control decision.

## Levels

- `verified`
- `assured`
- `limited`
- `unverified`

## Report Output

JSON reports include:

`report_trust_badge`

The dashboard payload includes:

`report_trust_badge`

The badge includes:

- `label`
- `level`
- `assurance_score`
- `replay_verified`
- `rbom_present`
- `provider_conformance_passed`
- `high_priority_evidence_gaps`
- `statement`
- `caveats`
- `risk_score_impact`

## Why This Matters

Stakeholders often need a short assurance signal, but CRIS-SME should not hide caveats.

The badge gives a concise label while preserving the underlying evidence, replay, RBOM, and conformance details.
