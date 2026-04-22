# History and Drift

CRIS-SME archives snapshots and computes drift-oriented comparisons.

## Snapshot Storage

- `outputs/reports/history/cris_sme_report_<timestamp>.json`

## Comparison Outputs

`history_comparison` includes:

- overall score deltas
- non-compliant finding deltas
- category score deltas
- control score deltas
- trend series
- new/resolved finding counts
- recurring regression counts
- priority distribution trend
- readiness trend

## Drift Interpretation

- **new findings**: present now, absent in previous run
- **resolved findings**: absent now, present in previous run
- **recurring regressions**: present in both with equal/higher current score

## Practical Usage

- track whether remediation is reducing risk
- identify domains with repeated regression
- build lightweight longitudinal evidence for governance reviews
