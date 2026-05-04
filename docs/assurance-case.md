# Assurance Case

The Assurance Case is a structured argument for why a CRIS-SME assessment can be trusted.

It does not create new risk scores.

It assembles:

- Claim Verification Pack
- Assessment Replay
- RBOM
- Assessment Assurance
- Evidence Gap Backlog
- Decision Provenance Graph
- Report Trust Badge

## Argument Structure

Each argument includes:

- `top_claim`
- `conclusion`
- `confidence`
- `supporting_claim_ids`
- `evidence_refs`
- `provenance_node_ids`
- `rbom_artifact_refs`
- `caveats`
- `residual_gaps`
- `reasoning`

## Report Output

CRIS-SME writes:

`outputs/reports/cris_sme_assurance_case.json`

Reports also include:

`assurance_case`

The dashboard payload includes:

`assurance_case`

The RBOM includes the assurance case as a hashed artifact.

## Current Top-Level Arguments

- This assessment is replayable and integrity-backed.
- Risk conclusions are traceable to scored findings and evidence references.
- Executive, compliance, and insurance claims are explicitly verified or caveated.
- Evidence quality and assurance gaps are explicit.

## Boundary

The Assurance Case never changes deterministic CRIS-SME risk scores.

It is an auditable argument layer above deterministic evidence, scoring, claims, and artifact integrity.
