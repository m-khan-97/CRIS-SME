# Provider Contract Conformance

Provider Contract Conformance turns CRIS-SME's provider support claims into executable checks.

The purpose is simple: CRIS-SME must never claim live multi-cloud coverage just because the schema can represent it.

## What It Checks

For each Provider Evidence Contract, CRIS-SME validates whether the declared support state matches implementation evidence.

Active provider support requires:

- adapter registered for active profile normalization
- live collector mode present
- provider collector or adapter tests present
- provider capability documentation present

Planned provider support requires:

- no active adapter registration
- no live collector mode
- provider capability documentation present

This distinction allows placeholder AWS/GCP adapter classes to exist without turning into unsupported product claims.

## Current Result

The current conformance gate expects:

- Azure: `active_ready`
- AWS: `planned_ready`
- GCP: `planned_ready`

Across the current policy pack:

- active contracts: 26
- planned contracts: 52
- total contracts: 78

## Report Output

JSON reports include:

- `provider_contract_conformance.passed`
- `provider_contract_conformance.active_contract_count`
- `provider_contract_conformance.planned_contract_count`
- `provider_contract_conformance.failed_contract_count`
- `provider_contract_conformance.provider_signals`
- `provider_contract_conformance.checks`

The dashboard payload includes a compact conformance summary under:

`confidence_and_evidence.provider_contract_conformance`

## Why This Is Important

This creates a product-grade guardrail for provider expansion.

Before AWS or GCP can be moved from planned to active, the implementation must satisfy the same contract that Azure satisfies today. That makes CRIS-SME's roadmap auditable, deterministic, and harder to overclaim.
