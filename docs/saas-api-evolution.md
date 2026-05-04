# SaaS and API Evolution

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

## Deployment Stages

### Stage 1: API Wrapper

Expose the existing pipeline behind an API without changing the engine.

Recommended first endpoints:

- create assessment
- fetch report
- list findings
- fetch finding trace

### Stage 2: Persistent Runs

Persist report outputs and lifecycle events in a database-ready structure.

Recommended store:

- PostgreSQL for tenant, run, finding, lifecycle, and exception objects
- object storage for full reports and generated artifacts

### Stage 3: Multi-Tenant Product

Add tenant isolation, user roles, API keys, audit logs, and scheduled assessments.

### Stage 4: MSP Console

Add portfolio risk, client comparison, recurring regression, exception expiry, and white-label reporting.

## Local-First Bridge

CRIS-SME should keep a private assessment option:

1. run collector locally
2. generate signed report bundle
3. upload summary bundle only if the customer chooses
4. verify report integrity in SaaS

This is a strong trust differentiator for privacy-sensitive SMEs.
