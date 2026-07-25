# Multi-Cloud Expansion

CRIS-SME is architected for provider-neutral decisions but currently Azure-first in active live collection.

## Current Reality

- Azure: active in adapter registry and live collector path
- AWS: adapter registered, research-preview boto3 collector (`AwsCollector`) covering IAM, Network, Data, Monitoring, Compute, Governance, and IoT — unit-tested against fake clients, not yet verified against a real AWS account
- GCP: adapter scaffold only (not active in registry for live runs)

## Expansion Goals

When adding AWS/GCP, preserve:

1. deterministic control semantics
2. explicit evidence lineage
3. observability-boundary honesty
4. provider-neutral report schema

## Suggested Implementation Sequence

1. Add provider-specific collectors that emit normalized profile/evidence records.
2. Register provider adapters only when coverage is test-backed.
3. Keep control IDs stable where semantics are equivalent.
4. Mark provider support status in policy metadata.
5. Add provider capability matrix and tests before claiming support.

## Required Guardrails

- Do not mark a provider as active unless there is:
  - adapter routing
  - collector evidence path
  - test coverage
  - documented limitations

- Do not force fake parity by copying Azure assumptions where provider semantics differ.

## Near-Term Practical Target

- keep Azure as the validated, `active` live path
- verify the AWS research-preview collector against a real AWS account, then graduate AWS provider contracts from `research_preview` to `active`/`supported`
- add richer mock GCP fixtures for cross-provider model testing
- graduate GCP to a live collector incrementally, following the same boto3-equivalent (google-cloud SDK) pattern AWS used
