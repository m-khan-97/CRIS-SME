# Policy Pack Changelog

The Policy Pack Changelog records why CRIS-SME policy-pack behavior changed.

It gives policy drift a machine-readable explanation trail.

## Purpose

When scores move, CRIS-SME needs to distinguish:

- evidence changed
- policy changed
- both changed
- neither changed

The changelog supports policy drift attribution by recording policy-pack changes with affected controls and expected impact.

## Data Source

The changelog lives in:

`data/policy_pack_changelog.json`

## Report Output

JSON reports include:

`policy_pack_changelog`

The dashboard payload includes:

`confidence_and_evidence.policy_pack_changelog`

Each entry includes:

- `version`
- `released_at`
- `change_type`
- `control_ids`
- `title`
- `summary`
- `risk_score_impact`
- `evidence_impact`

## Boundary

The changelog does not score findings.

It explains policy-pack changes so replay, evidence diff, and control drift attribution can remain auditable.
