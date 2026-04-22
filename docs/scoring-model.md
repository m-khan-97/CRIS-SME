# Scoring Model

CRIS-SME scoring is deterministic and explainable by design.

## Inputs

Each finding contributes:

- severity
- exposure
- data sensitivity
- confidence (observed + calibrated)
- remediation effort
- category

Only non-compliant findings are scored into risk outputs.

## Base Severity Weights

- Critical = 10
- High = 7
- Medium = 4
- Low = 1

## Score Formula

```
likelihood_factor = 0.8 + (0.8 * exposure)
data_factor       = 0.8 + (0.8 * data_sensitivity)
confidence_factor = 0.7 + (0.3 * calibrated_confidence)
remediation_factor = 1.0 + (0.15 * remediation_effort)

raw_score =
  severity_weight
  * likelihood_factor
  * data_factor
  * confidence_factor
  * remediation_factor
```

Raw score is normalized to 0-100 with bounded headroom.

## Category Aggregation

Domain scores are average non-compliant finding scores per category.

Overall weighted score:

- IAM: 25%
- Network: 20%
- Data: 20%
- Monitoring/Logging: 15%
- Compute/Workloads: 10%
- Cost/Governance Hygiene: 10%

## Priority Bands

- `Immediate`: score >= 75
- `High`: score >= 50
- `Planned`: score >= 25
- `Monitor`: score < 25

## Confidence Calibration

Calibrated confidence blends observed confidence with control-level empirical agreement metadata.

- validated controls: stronger empirical weighting
- provisional controls: lighter empirical weighting
- unmapped controls: observed confidence retained

Calibration metadata is explicit in output artifacts.

## Context-Aware Signals

Graph-context outputs (blast radius, toxic combinations, exposure chains) augment prioritization context but do not replace deterministic scoring math.

This separation keeps CRIS-SME auditable and stable.

## What Scoring Is Not

- not a black-box ML model
- not a legal/compliance certification score
- not a direct incident-probability predictor

It is a deterministic governance risk prioritization model.
