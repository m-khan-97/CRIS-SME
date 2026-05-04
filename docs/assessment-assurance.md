# Assessment Assurance

Assessment Assurance grades the trustworthiness of a CRIS-SME assessment artifact.

It is separate from risk scoring.

Risk score answers:

> How risky is the cloud posture?

Assessment Assurance answers:

> How reproducible, traceable, and well-evidenced is this assessment artifact?

## Important Boundary

Assessment Assurance never changes deterministic CRIS-SME risk scores.

It is a trust layer around the report, not an input into prioritization.

## Signals

The assurance score combines non-risk signals:

- deterministic replay
- Risk Bill of Materials presence
- provider contract conformance
- evidence sufficiency
- Decision Ledger presence
- collector coverage metadata

Each signal has:

- `signal_id`
- `label`
- `score`
- `weight`
- `passed`
- `explanation`

## Report Output

JSON reports include:

`assessment_assurance`

The dashboard payload includes:

`assessment_assurance.assurance_score`

and:

`assessment_assurance.assurance_level`

## Why This Matters

Two reports can have the same cloud risk score but different assurance levels.

For example:

- a live Azure report with replay, RBOM, provider conformance, and sufficient evidence should have high assurance
- a partial collector run with unavailable evidence should still be explainable, but its assurance should be lower

This makes CRIS-SME more honest than generic scanning tools that collapse risk, confidence, evidence quality, and report integrity into one opaque severity label.
