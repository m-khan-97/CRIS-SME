# Control Drift Attribution

Control Drift Attribution explains why risk movement happened between two CRIS-SME assessment reports.

It separates:

- evidence drift
- policy-pack drift
- collector or coverage drift
- lifecycle and exception-state drift
- new findings
- resolved findings

## Why It Exists

Historical score movement is ambiguous unless CRIS-SME can say what changed.

A higher risk score might mean:

- the cloud posture got worse
- the collector saw more evidence
- the policy pack changed
- an exception expired
- a finding became newly observable

Control Drift Attribution keeps those causes separate.

## Report Output

JSON reports include:

`control_drift_attribution`

The dashboard payload includes:

`control_drift_attribution`

Each attribution item includes:

- `control_id`
- `current_score`
- `previous_score`
- `delta`
- `direction`
- `attribution`
- `contributing_factors`
- current and previous priority

## Attribution Labels

- `evidence_drift`
- `policy_drift`
- `mixed_evidence_policy_drift`
- `collector_coverage_drift`
- `lifecycle_exception_drift`
- `new_finding`
- `resolved_finding`
- `unchanged`

## Boundary

This layer does not change CRIS-SME scoring.

It explains score movement after deterministic scoring has already happened.
