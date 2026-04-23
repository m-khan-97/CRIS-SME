# Dashboard

CRIS-SME produces a premium interactive local dashboard:

- `outputs/reports/cris_sme_dashboard_payload.json`
- `outputs/reports/cris_sme_dashboard.html`

For publication and demos, the same outputs are assembled into a deployable static bundle:

- `dist/site/index.html`
- `dist/site/dashboard.html`
- `dist/site/data/cris_sme_dashboard_payload.json`

## What It Shows

1. Executive overview
2. Domain score breakdown
3. Trend and drift indicators
4. Filterable finding explorer
5. Compliance/readiness summary
6. Confidence/evidence quality
7. Graph-context insights
8. Remediation and exceptions summary

## Dashboard Data Contract

Built from report payload sections:

- `executive_overview`
- `domain_breakdown`
- `trend`
- `finding_explorer`
- `compliance_readiness`
- `confidence_and_evidence`
- `graph_context`
- `remediation`
- `exceptions_and_governance`

## Operator Notes

- The dashboard is static-asset local HTML with embedded payload.
- Filtering and interactions are client-side.
- No external backend is required for home-lab usage.
