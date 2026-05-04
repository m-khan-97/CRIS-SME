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
- `evidence_sufficiency`
  - sufficiency label
  - provider support state
  - declared evidence requirements
  - satisfied and missing requirements
  - known limitation notes
- `confidence_calibration`
- `decision_rationale`

## Observation Classes

- `observed`: direct evidence available
- `inferred`: conclusion from partial evidence
- `unavailable`: required evidence not observable

This distinction is used to prevent false certainty.

## Evidence Sufficiency

CRIS-SME separates observation class from evidence sufficiency.

Observation class describes how the evidence was obtained. Evidence sufficiency describes whether the available evidence is strong enough for the control decision.

Supported sufficiency states:

- `sufficient`: direct evidence satisfies the current control evidence requirements
- `partial`: some direct evidence exists, but declared requirements are incomplete
- `inferred`: the decision depends on partial evidence or scope context
- `unavailable`: required evidence is not observable in the current scope
- `stale`: evidence exists but is older than the expected freshness window
- `unsupported`: the provider path is not actively supported for this control

This model is central to CRIS-SME's innovation direction because it prevents partial observability from being hidden inside a single confidence score.

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
