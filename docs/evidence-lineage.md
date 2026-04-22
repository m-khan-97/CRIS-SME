# Evidence Lineage

CRIS-SME findings are now traceable to evidence and rule metadata.

## Per-Finding Lineage Fields

Each prioritized finding includes:

- `finding_id` (stable deterministic ID)
- `control_id`
- `rule_version`
- `finding_trace`
  - `evidence_refs`
  - `failed_conditions`
  - `observation_class`
  - evidence count split (direct/inferred/unavailable)
- `confidence_calibration`
- `decision_rationale`

## Observation Classes

- `observed`: direct evidence available
- `inferred`: conclusion from partial evidence
- `unavailable`: required evidence not observable

This distinction is used to prevent false certainty.

## Collector Coverage

Report-level `collector_coverage` describes:

- observed domains
- partially observed domains
- unavailable domains
- evidence quality note

## Policy and Rule Governance Tie-In

Control metadata from policy specs is embedded in finding metadata:

- rule version
- intent/applicability
- known limitations
- provider support status
