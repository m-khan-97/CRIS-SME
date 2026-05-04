# Customer-Facing Assurance Portal

The Assurance Portal is a static HTML view designed for customers, auditors, insurers, and non-technical stakeholders.

It focuses on trust rather than operator workflow.

## It Shows

- Report Trust Badge
- Assurance score and conclusion
- deterministic replay status
- RBOM integrity status
- evidence gap counts
- Claim-Bound Narrative
- Assurance Case arguments
- verified and caveated claims
- top Decision Provenance paths

## Output

CRIS-SME writes:

`outputs/reports/cris_sme_assurance_portal.html`

The Vercel/static site bundle includes:

`dist/site/assurance.html`

The static site index links to the Assurance Portal next to the dashboard and technical report.

## Boundary

The Assurance Portal does not introduce new findings, claims, or scores.

It is a customer-facing rendering of existing deterministic assurance artifacts.
