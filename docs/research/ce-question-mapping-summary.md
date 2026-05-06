# Cyber Essentials Danzell Mapping Summary

> Status: first-pass research mapping.  
> This summary is derived from `data/ce_question_mapping.json` and uses paraphrased local descriptions only.

## Source Version

- Scheme: Cyber Essentials
- Question set: Danzell
- Question set version: `16.2`
- Effective period: from `2026-04-27`
- Requirements version: `3.3`
- Official preview page: https://iasme.co.uk/cyber-essentials/preview-the-self-assessment-questions-for-cyber-essentials/

## Mapping Scope

The first pass maps `106` Danzell preparation entries.

This count is larger than the often-cited number of technical assessment questions because the preparation booklet includes:

- organisation and certificate context
- scope declaration
- insurance questions
- technical-control questions
- conditional follow-up entries
- free-text preparation entries

For the paper, report both:

- all mapped entries: `106`
- technical-control entries: `62`

## All-Entry Evidence Coverage

| Evidence class | Count | Percentage |
| --- | ---: | ---: |
| `direct_cloud` | `5` | `4.7%` |
| `inferred_cloud` | `23` | `21.7%` |
| `endpoint_required` | `24` | `22.6%` |
| `policy_required` | `19` | `17.9%` |
| `manual_required` | `35` | `33.0%` |
| `not_observable` | `0` | `0.0%` |

## Technical-Control Evidence Coverage

| Evidence class | Count | Percentage |
| --- | ---: | ---: |
| `direct_cloud` | `5` | `8.1%` |
| `inferred_cloud` | `17` | `27.4%` |
| `endpoint_required` | `21` | `33.9%` |
| `policy_required` | `18` | `29.0%` |
| `manual_required` | `1` | `1.6%` |
| `not_observable` | `0` | `0.0%` |

## Research Interpretation

The strongest finding is not that Cyber Essentials can be fully automated from cloud telemetry. It cannot.

The stronger and more defensible result is:

> A meaningful minority of Cyber Essentials technical-control questions can be directly or inferentially supported from cloud telemetry, but endpoint and policy evidence remain essential for a complete self-assessment.

In the first pass:

- `22` of `62` technical-control entries are direct or inferred cloud candidates.
- `21` of `62` technical-control entries require endpoint, MDM, EDR, or local device evidence.
- `18` of `62` technical-control entries require policy, process, approval, or business-need evidence.

This supports the paper framing:

> CRIS-SME pre-populates the cloud-observable subset and routes the rest to human or endpoint-evidence review with explicit evidence sufficiency labels.

## High-Value CRIS-SME Coverage Areas

Best current fit:

- public inbound exposure
- permissive network rules
- externally reachable services
- public storage exposure
- privileged role assignment tracking
- administrator MFA and Conditional Access evidence when Graph permissions allow it
- RBAC overprivilege signals
- cloud resource inventory

Most important future integrations:

- Microsoft Graph MFA registration details
- Entra PIM and access reviews
- Defender for Endpoint
- Intune device compliance
- Azure Update Manager
- SaaS/cloud app discovery
- change-management evidence for firewall and access approvals

## Paper Claim

Recommended claim:

> CRIS-SME provides an evidence-sufficiency-aware Cyber Essentials answer pre-population layer that maps question-level assessment entries to live cloud evidence, endpoint evidence requirements, policy requirements, and manual-review boundaries.

Avoid:

> CRIS-SME automates Cyber Essentials certification.

