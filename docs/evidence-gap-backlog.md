# Evidence Gap Backlog

The Evidence Gap Backlog turns missing or partial evidence into actionable product work.

It is not a customer remediation list. It is a CRIS-SME improvement backlog for:

- collector enrichment
- provider activation
- evidence sufficiency improvement
- assessment assurance improvement

## Sources

Backlog items are generated from:

- prioritized findings with partial, inferred, stale, or unavailable evidence
- missing evidence requirements
- Provider Evidence Contracts marked `planned`

## Item Types

`finding_evidence_gap`

Evidence is weak for a current finding. The recommended action is to enrich collector evidence or preserve the limitation until direct evidence is available.

`provider_activation_gap`

A provider path exists in the contract catalog but is still planned. The recommended action follows the contract activation gate.

## Report Output

JSON reports include:

`evidence_gap_backlog`

The dashboard payload includes:

`confidence_and_evidence.evidence_gap_backlog`

Each item includes:

- `gap_id`
- `gap_type`
- `provider`
- `domain`
- `control_id`
- `priority`
- `evidence_gap`
- `recommended_action`
- `assurance_impact`

## Why This Matters

CRIS-SME should improve its evidence quality deliberately.

Instead of saying "AWS/GCP planned" or "IAM evidence partial" as static caveats, the backlog converts those caveats into a controlled engineering queue.
