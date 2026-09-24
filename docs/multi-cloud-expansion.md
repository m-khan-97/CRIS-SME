# Multi-Cloud Expansion

> Provider design background. The [canonical roadmap](roadmap.md) owns expansion priorities, validation gates and release decisions; this document is not a separate implementation plan.

CRIS-SME is architected for provider-neutral decisions but currently Azure-first in active live collection.

## Current Reality

- Azure: active in adapter registry and live collector path
- AWS: adapter registered, research-preview boto3 collector (`AwsCollector`) covering IAM, Network, Data, Monitoring, Compute, Governance, and IoT. Unit fixtures and recorded live assessment artifacts do not establish complete provider validation; graduation requires the roadmap's service-specific evidence gates.
- GCP: adapter scaffold only (not active in registry for live runs)

## Expansion Goals

When adding AWS/GCP, preserve:

1. deterministic control semantics
2. explicit evidence lineage
3. observability-boundary honesty
4. provider-neutral report schema

## Execution Reference

Use phase P2 of the [canonical roadmap](roadmap.md). Stable IDs, provider capability metadata and documented semantic equivalence are required; a normalized schema alone does not establish equivalent detection coverage.

## Required Guardrails

- Do not mark a provider as active unless there is:
  - adapter routing
  - collector evidence path
  - test coverage
  - documented limitations

- Do not force fake parity by copying Azure assumptions where provider semantics differ.

## Provider Graduation

Promote only the service/control scope supported by reproducible tests and reviewed live evidence. Broader GCP, Kubernetes and IaC work is demand-gated in the canonical roadmap, not an automatic next step after AWS.
