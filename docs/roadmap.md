# Roadmap

This roadmap tracks CRIS-SME's evolution from deterministic assessment engine into a state-of-the-art evidence-driven cloud risk decision methodology for SMEs.

## Completed Foundations

- deterministic control + scoring engine
- confidence calibration layer
- compliance mapping and UK-readiness outputs
- rich export surfaces (technical + executive + insurer)
- history snapshots and drift comparison
- graph-context summaries (blast radius / toxic combinations / chain hints)
- finding lifecycle and exception model
- dashboard payload + interactive dashboard HTML
- control-spec governance metadata pack
- GitHub Actions CI/CD + Vercel-ready static publication pipeline

## Product Themes

### Decision System Of Record

- Decision Ledger for finding, exception, approval, and score-change history
- signed report manifests
- Risk Bill of Materials
- stable policy-pack and scoring-model versioning

### Evidence Quality And Assurance

- evidence sufficiency state per control
- evidence freshness and completeness scoring
- stronger collector coverage contracts
- provider capability conformance tests
- provider evidence contracts for active/planned/unsupported support claims

### Remediation Intelligence

- deterministic remediation simulator
- expected risk reduction per action
- owner, due date, status, and cost tracking
- recurring regression detection tied to action history

### API And Future Delivery

- assessment and report API
- persistent run history
- tenant/workspace/cloud-account model
- multi-tenant MSP portfolio dashboard
- customer-ready onboarding and least-privilege collector setup

### Stakeholder Experience

- role-based dashboard views for owner, engineer, board, insurer, and MSP users
- insurer questionnaire evidence export
- board pack and audit appendix improvements
- AI narrator as a non-authoritative explanation layer

## Near-Term Priorities: 0-30 Days

1. deepen live Azure identity/governance evidence paths
2. improve budget governance evidence collection in live mode
3. expand dashboard interactions (deeper drill-down, richer graph views)
4. harden lifecycle workflows with action ownership and state transitions
5. add evidence sufficiency states to finding lineage
6. extend Risk Bill of Materials with cryptographic signing and verification command
7. extend Decision Ledger with owner/approval events and export views
8. expand remediation simulator with custom scenario input and report exports

## Medium-Term Priorities: 31-60 Days

1. activate mock-backed AWS/GCP provider validation paths
2. add richer provider capability contracts and conformance tests
3. introduce optional policy-as-code adapter surface (while keeping deterministic core)
4. increase longitudinal benchmarking depth with more snapshots/environments
5. add API wrapper for assessments, findings, traces, exceptions, and reports
6. add insurer questionnaire export with evidence confidence labels
7. formalize local/private assessment bundle upload model

## Longer-Term Direction: 61-90 Days And Beyond

1. graduate AWS/GCP collectors to active support when coverage is real
2. strengthen attack-path style context while staying explainable
3. package reusable API/dashboard deployment profile for small teams
4. add controlled AI-assisted prioritization experiments as overlay, never replacement
5. add MSP portfolio console
6. produce a UKRI-ready innovation brief
7. run technical validation with SMEs, MSPs, and assurance stakeholders when the methodology is stronger
