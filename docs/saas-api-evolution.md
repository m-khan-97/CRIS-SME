# SaaS and API Evolution

> API design background, not a separate delivery plan. Use the [canonical roadmap](roadmap.md) for authentication, tenancy, persistence and release sequencing. Objects and endpoints below are design concepts unless independently implemented and tested.

CRIS-SME currently runs as a deterministic CLI/reporting pipeline with static dashboard outputs. The next product step is to preserve that local-first strength while adding a SaaS/API plane.

## Principles

- The deterministic engine remains independent from the SaaS layer.
- Local/private assessment remains a first-class mode.
- APIs expose evidence, decisions, reports, and lifecycle state without changing scoring rules.
- Every API object should carry version and provenance metadata.

## Core SaaS Objects

- `tenant`: customer or MSP account
- `workspace`: operational boundary such as client, business unit, or environment
- `cloud_account`: provider account/subscription/project under assessment
- `assessment_run`: one deterministic assessment execution
- `evidence_record`: raw or normalized evidence with source, freshness, and hash
- `asset`: normalized cloud asset
- `asset_relationship`: graph edge between assets
- `finding`: deterministic control decision
- `finding_lifecycle_event`: status, ownership, exception, and approval history
- `exception_record`: accepted risk or suppression with expiry and compensating control
- `action_item`: remediation task with owner, cost tier, and expected risk reduction
- `report_artifact`: JSON, HTML, dashboard, insurance, appendix, board, or benchmark export
- `policy_pack`: versioned control and mapping bundle

## API Surface

### Assessments

- `POST /assessments`
- `GET /assessments/{assessment_id}`
- `GET /assessments/{assessment_id}/status`
- `GET /assessments/{assessment_id}/run-metadata`

### Evidence

- `GET /assessments/{assessment_id}/evidence`
- `GET /evidence/{evidence_id}`
- `GET /assessments/{assessment_id}/collector-coverage`

### Findings

- `GET /assessments/{assessment_id}/findings`
- `GET /findings/{finding_id}`
- `GET /findings/{finding_id}/trace`
- `GET /findings/{finding_id}/score-breakdown`

### Lifecycle

- `POST /findings/{finding_id}/assign`
- `POST /findings/{finding_id}/status`
- `POST /exceptions`
- `GET /exceptions`
- `POST /exceptions/{exception_id}/renew`
- `POST /exceptions/{exception_id}/expire`

### Reports

- `GET /assessments/{assessment_id}/reports/json`
- `GET /assessments/{assessment_id}/reports/dashboard`
- `GET /assessments/{assessment_id}/reports/executive`
- `GET /assessments/{assessment_id}/reports/insurance`
- `GET /assessments/{assessment_id}/reports/appendix`

### Simulation

- `POST /simulations/remediation`
- `POST /simulations/policy-pack`
- `GET /simulations/{simulation_id}`

### Policy Packs

- `GET /policy-packs`
- `GET /policy-packs/{policy_pack_id}`
- `GET /policy-packs/{policy_pack_id}/controls`
- `GET /policy-packs/{policy_pack_id}/provider-support`

## Delivery Reference

The [canonical roadmap](roadmap.md) replaces the former staged plan. Hosted deployment requires authenticated tenant isolation and recovery testing before exposure, not as an optional later stage. PostgreSQL metadata and tenant-scoped artifact storage are the proposed target.

## Local-First Bridge

CRIS-SME should keep a private assessment option:

1. run collector locally
2. generate signed report bundle
3. upload summary bundle only if the customer chooses
4. verify report integrity in SaaS

This is a strong trust differentiator for privacy-sensitive SMEs.
