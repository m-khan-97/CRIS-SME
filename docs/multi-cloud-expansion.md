# Multi-Cloud Expansion Plan

This document defines how CRIS-SME can grow from an Azure-first implementation into a broader provider-neutral framework spanning AWS and GCP.

## Strategic Position

CRIS-SME should remain:

- provider-neutral at the core
- Azure-first in current implementation
- explicitly staged in its cloud expansion

This matters for research credibility. A vague claim of “multi-cloud support” would be weaker than a clearly phased plan with an Azure reference implementation and a documented adapter strategy.

## Current State

Already provider-neutral:

- core cloud profile model
- scoring engine
- compliance mapping
- reporting pipeline
- archived-run comparison
- figure and appendix generation

Currently Azure-first:

- live collection
- adapter registration
- case-study evidence
- live report validation

## Expansion Principles

AWS and GCP support should follow four rules:

1. normalize into the same internal `CloudProfile`
2. keep control semantics aligned where possible
3. make provider-specific evidence explicit in metadata
4. preserve observability boundaries rather than hiding them

## AWS Adapter Direction

Planned AWS collection path:

- Organizations and account context for scope
- IAM role and policy posture
- Security groups and public exposure
- S3 and KMS data controls
- CloudTrail and GuardDuty monitoring posture
- EC2 workload posture
- tagging and Config/rule coverage

Likely normalization approach:

- IAM: privileged principals, stale access keys or workload credentials, role-review freshness
- Network: exposed SSH/RDP, permissive security groups, public endpoints
- Data: public buckets, encryption posture, retention or backup coverage
- Monitoring: CloudTrail, alerts, GuardDuty, logging centralization
- Compute: instance hardening, agent coverage, backup posture
- Governance: tags, budgets, Config coverage, orphaned assets

## GCP Adapter Direction

Planned GCP collection path:

- project or organization scope
- IAM binding posture and privileged roles
- firewall rules and public ingress exposure
- Cloud Storage and KMS data controls
- Cloud Logging, SCC, and alerting posture
- Compute Engine workload posture
- labels, budgets, and policy/governance coverage

Likely normalization approach:

- IAM: privileged members, service account hygiene, access review posture
- Network: permissive firewall rules, exposed admin services, public service endpoints
- Data: public buckets, encryption signals, backup or retention posture
- Monitoring: audit logging, alerting, SCC-style coverage
- Compute: workload hardening, agent posture, patch or configuration baselines
- Governance: labels, budgets, organization policy, orphaned resources

## Adapter Implementation Path

Recommended implementation order:

1. add placeholder AWS and GCP adapters
2. keep them unregistered until collection paths are ready
3. create provider-specific raw posture record shapes behind the collectors layer
4. reuse the existing control and reporting pipeline without branching the scoring model

This allows CRIS-SME to expand clouds without rebuilding the entire framework for each provider.

## Research Value of Multi-Cloud Expansion

Extending to AWS and GCP would support several research angles:

- comparison of governance risk patterns across providers
- evaluation of provider-specific observability boundaries
- testing whether deterministic scoring remains stable under different provider evidence
- comparative analysis of SME cloud misconfiguration themes across environments

## Practical Next Steps

Short-term:

- add AWS and GCP adapter placeholders to the providers package
- document expected metadata fields for provider-specific evidence counts
- preserve Azure as the primary validated live path

Medium-term:

- implement mock AWS and GCP raw-profile fixtures
- run the current controls against those mock profiles
- evaluate which controls remain provider-neutral and which require provider-specific variants

Long-term:

- add live AWS and GCP collectors
- compare archived run histories across provider modes
- extend paper evaluation to multi-provider case studies
