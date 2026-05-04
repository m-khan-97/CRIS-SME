# Decision Review Queue

The Decision Review Queue converts CRIS-SME outputs into explicit governance decisions.

It is generated from:

- prioritized risk findings
- evidence sufficiency
- evidence gap backlog
- lifecycle and exception status

## Decision Types

- `remediation_decision`
- `evidence_review`
- `evidence_investigation`
- `exception_review`
- `monitor`

## Report Output

JSON reports include:

`decision_review_queue`

The dashboard payload includes:

`decision_review_queue`

Each item includes:

- `review_id`
- `decision_type`
- `control_id`
- `finding_id`
- `priority`
- `recommended_decision`
- `rationale`
- `owner_hint`

## Why This Matters

CRIS-SME should not stop at finding generation.

For SMEs, the hard part is often deciding what to do next: fix, investigate, accept, suppress, or monitor.

The Decision Review Queue makes that governance step explicit while keeping the deterministic risk score unchanged.
