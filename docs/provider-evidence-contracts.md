# Provider Evidence Contracts

Provider Evidence Contracts make CRIS-SME's provider support explicit at control level.

They answer:

- which providers are active, planned, or unsupported for each control?
- what evidence is required for a sufficient decision?
- how fresh should that evidence be?
- what confidence penalties apply when evidence is partial?
- what provider identity, auth mode, and scope rules apply?
- what least-privilege permissions are required?
- what provider capabilities can collect resource-level evidence?
- what limitations must remain visible in reports?
- what gate must be satisfied before planned provider support can be claimed?

## Why This Matters

CRIS-SME is provider-neutral in architecture but Azure-first in live collection. Without explicit contracts, it would be too easy to overclaim AWS or GCP readiness.

Provider Evidence Contracts prevent fake parity by making provider support auditable.

CRIS-SME also includes an executable conformance gate for these contracts. See
[Provider Contract Conformance](provider-contract-conformance.md).

## Contract Fields

Each contract includes:

- `contract_id`
- `provider`
- `control_id`
- `control_version`
- `domain`
- `support_status`
- `evidence_requirements`
- `freshness_hours`
- `sufficiency_policy`
- `confidence_penalty_rules`
- `known_limitations`
- `activation_gate`
- `identity`
- `scopes`
- `auth`
- `permissions`
- `evidence_capabilities`
- `freshness_policy`
- `limitations`

The expanded fields are intentionally explicit:

- `identity`: provider account/tenant labels and identity sources, such as Azure subscription plus tenant context.
- `scopes`: supported collection scopes and scope limitations, such as tenant, subscription, and resource group.
- `auth`: supported authentication modes and secret-handling posture.
- `permissions`: required and optional least-privilege permissions for the provider/control path.
- `evidence_capabilities`: collection method, resource types, resource-level evidence support, and freshness-check support.
- `freshness_policy`: when evidence becomes stale and how stale evidence should be handled.
- `limitations`: provider-specific limitations that must remain visible in assurance outputs.

For the active Azure path, see [Azure Least-Privilege Setup](azure-least-privilege-setup.md)
and the custom role artifact at
`infra/azure/role-definitions/cris-sme-assessment-reader.json`.

## Support States

- `active`: implemented and reportable for the provider path
- `planned`: model-ready but not live-supported
- `unsupported`: not currently available for that provider

The current policy pack marks Azure controls as active and AWS/GCP controls as planned.

## Report Output

CRIS-SME reports include:

- `provider_evidence_contracts.contract_schema_version`
- `provider_evidence_contracts.policy_pack_version`
- `provider_evidence_contracts.provider_count`
- `provider_evidence_contracts.control_count`
- `provider_evidence_contracts.contract_count`
- `provider_evidence_contracts.support_status_counts`
- `provider_evidence_contracts.contracts`
- `provider_contract_conformance`

## Activation Gate

A planned provider path should only be marked active after:

- collector evidence exists
- adapter routing is implemented
- tests cover the provider path
- limitations are documented
- identity, scope, auth, permission, capability, freshness, and limitation metadata is complete
- evidence sufficiency behavior is visible in reports

This is a core guardrail for CRIS-SME's multi-cloud expansion.
