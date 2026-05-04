# Security and Trust Model

CRIS-SME should earn trust by being explicit about what it collects, what it stores, what it can prove, and where its visibility ends.

## Trust Principles

- Read-only evidence collection by default.
- Least-privilege cloud permissions.
- Deterministic decisions with versioned scoring logic.
- No hidden AI-generated findings or score changes.
- Explicit observability boundaries.
- Customer-controlled retention and deletion.
- Local/private execution remains supported.

## Collector Trust

Collectors should document:

- required permissions
- optional permissions
- evidence collected
- evidence not collected
- freshness assumptions
- provider API limitations
- known false-negative and partial-observability boundaries

Azure-first trust work should prioritize:

- least-privilege role assignment guidance
- Entra identity evidence boundaries
- Conditional Access visibility requirements
- Defender/Policy/Budget visibility requirements
- clear handling when permissions are insufficient

## Data Handling

Production SaaS should classify data into:

- raw cloud evidence
- normalized evidence records
- asset graph data
- findings and score outputs
- lifecycle and exception records
- generated reports
- AI narrator prompts and responses

Recommended controls:

- encryption in transit and at rest
- tenant-level data isolation
- customer-configurable retention
- deletion workflow
- object-level access checks
- audit logs for report access and exception changes

## Report Integrity

CRIS-SME should add signed report manifests.

The manifest should include:

- report hash
- run ID
- generated timestamp
- engine version
- schema version
- policy-pack version
- scoring model version
- collector mode
- providers in scope
- evidence record hashes
- report artifact hashes

This becomes the foundation for a Risk Bill of Materials.

## AI Trust Boundary

AI is an optional narrator. It must never:

- create a finding
- alter a score
- remove a finding
- claim compliance certification
- invent evidence
- answer an insurer question without evidence support

AI output should cite deterministic fields such as:

- finding ID
- control ID
- score
- priority
- evidence refs
- observation class
- confidence label

## SaaS Security Roadmap

### Minimum Production Baseline

- SSO-ready authentication model
- tenant isolation
- role-based access control
- API keys with scoping and rotation
- audit logging
- dependency scanning
- CodeQL
- signed reports
- secrets management

### Customer Trust Roadmap

- public security page
- subprocessors and data retention policy
- least-privilege collector documentation
- vulnerability disclosure process
- SBOM export
- SOC 2 readiness controls
- private deployment option for sensitive customers

## Product Trust Statement

CRIS-SME does not hide uncertainty. If evidence is unavailable, partial, stale, or inferred, the product records that state and keeps it visible in scoring, reporting, and stakeholder outputs.
