# Decision Provenance Graph

The Decision Provenance Graph links CRIS-SME evidence, controls, findings, scores, assurance, and governance decisions into one traceable graph.

It answers:

- which evidence snapshot produced this finding?
- which policy pack and control defined the decision?
- which provider evidence contract set evidence expectations?
- how was the finding scored?
- was evidence sufficient?
- did the finding require governance review?
- how does replay, RBOM, assurance, and trust badge relate to the final report?

## Graph Path

A typical decision path is:

`Evidence Snapshot -> Policy Pack -> Control -> Provider Evidence Contract -> Finding -> Evidence Sufficiency -> Score -> Decision Review -> Assessment Assurance -> Report Trust Badge`

## Report Output

JSON reports include:

`decision_provenance_graph`

CRIS-SME also writes:

`outputs/reports/cris_sme_decision_provenance_graph.json`

The RBOM includes this graph as a hashed report artifact.

## Node Types

Current node types include:

- `evidence_snapshot`
- `policy_pack`
- `control`
- `provider_evidence_contract`
- `finding`
- `evidence_sufficiency`
- `score`
- `decision_review_item`
- `assessment_replay`
- `risk_bill_of_materials`
- `control_drift_attribution`
- `assessment_assurance`
- `report_trust_badge`

## Boundary

The graph does not change CRIS-SME risk scoring.

It records how deterministic decisions, evidence quality, integrity metadata, and governance actions connect.
