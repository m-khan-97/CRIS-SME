# Cyber Essentials Question Coverage Analysis

> Status: research working note.  
> This file intentionally avoids copying the IASME Cyber Essentials question set verbatim. It records paraphrased requirement areas, evidence-sufficiency classes, and the annotation method for a future question-level answer pack.

## Purpose

This document defines the research scope for a second CRIS-SME paper:

**Evidence-sufficiency-aware pre-population of Cyber Essentials self-assessments from cloud telemetry.**

The goal is not to automate certification. The goal is to determine which Cyber Essentials questions can be pre-populated from cloud control-plane evidence, which questions require endpoint or MDM evidence, and which remain human or policy assertions.

## Source Boundary

Primary public sources:

- NCSC Cyber Essentials overview: https://www.ncsc.gov.uk/cyberessentials/overview
- IASME Cyber Essentials self-assessment question preview page: https://iasme.co.uk/cyber-essentials/preview-the-self-assessment-questions-for-cyber-essentials/
- Current question set used for the first mapping pass: Cyber Essentials Danzell, version `16.2`, April 2026
- Current requirements version referenced by IASME for Danzell: NCSC Requirements for IT Infrastructure v3.3
- Historical source used during initial scoping: NCSC Cyber Essentials Requirements for IT infrastructure v3.1, April 2023: https://www.ncsc.gov.uk/files/Cyber-Essentials-Requirements-for-Infrastructure-v3-1-January-2023.pdf
- Microsoft Defender for Cloud regulatory compliance standards: https://learn.microsoft.com/en-us/azure/defender-for-cloud/concept-regulatory-compliance-standards

Important source note:

- NCSC links to IASME for the downloadable Cyber Essentials question set.
- The IASME question text may have reuse restrictions.
- CRIS-SME should not publish verbatim question text until the licence position is confirmed.
- The implementation should use stable internal question IDs, paraphrased descriptions, and source references rather than copying full question wording.
- The machine-readable mapping in `data/ce_question_mapping.json` is paraphrased and records evidence classes only.

## Research Claim

Preferred claim:

> CRIS-SME classifies Cyber Essentials self-assessment questions by evidence sufficiency and pre-populates the cloud-observable subset from live cloud telemetry, while explicitly flagging endpoint, policy, and human-verification boundaries.

Avoid:

> CRIS-SME automates Cyber Essentials certification.

Avoid:

> CRIS-SME answers the Cyber Essentials questionnaire automatically.

## Evidence Classes

| Class | Meaning | Example evidence path |
| --- | --- | --- |
| `direct_cloud` | A cloud control-plane API can directly support a proposed answer. | Azure NSG rules show public inbound SSH/RDP exposure. |
| `inferred_cloud` | Cloud telemetry supports a cautious inference but not a full answer. | Defender coverage ratio suggests workload protection but not all endpoint malware controls. |
| `endpoint_required` | Requires endpoint, MDM, EDR, patch, local firewall, or device inventory. | Laptop firewall state, local AV status, device unlock configuration. |
| `policy_required` | Requires organisational process, approval, contractual, or documentation evidence. | Documented business need, approval records, security policy ownership. |
| `manual_required` | Requires human confirmation even if supporting telemetry exists. | Scope boundary, asset ownership, third-party device interpretation. |
| `not_observable` | Not observable from CRIS-SME's current Azure collector. | Unsupported SaaS configuration or unmanaged BYOD state. |

## Paper Reframe

The paper should foreground the coverage boundary:

> CRIS-SME operates at the cloud control-plane layer. Cyber Essentials requirements concerning endpoint devices, mobile devices, BYOD, local software, and organisational process are classified as endpoint-required, policy-required, or manual-required. The paper evaluates how much of the CE self-assessment can be evidenced from cloud telemetry alone, and how safely the remaining questions can be routed to human review.

The central empirical result should be a coverage table:

| Coverage category | Count | Percentage |
| --- | ---: | ---: |
| Directly observable from Azure cloud telemetry | `5` | `4.7%` |
| Inferable from Azure cloud telemetry with caveats | `23` | `21.7%` |
| Requires endpoint / MDM / EDR telemetry | `24` | `22.6%` |
| Requires organisational or policy confirmation | `54` | `50.9%` |
| Not observable in current CRIS-SME scope | `0` | `0.0%` |

First-pass mapping scope:

- total Danzell entries mapped: `106`
- technical-control entries mapped: `62`
- technical-control entries classified as `direct_cloud`: `5`
- technical-control entries classified as `inferred_cloud`: `17`
- technical-control entries classified as `endpoint_required`: `21`
- technical-control entries classified as `policy_required`: `18`
- technical-control entries classified as `manual_required`: `1`

Interpretation:

The current question set contains more than the often-quoted 56 technical questions because it includes organisation, scope, insurance, conditional, and free-text preparation entries. The research paper should report both all-question coverage and technical-control-only coverage.

## Preliminary Requirement-Level Coverage

This is a first-pass annotation at the public requirements level, not a final IASME question-level annotation.

| CE pillar | Requirement area | Cloud telemetry coverage | Likely CRIS-SME evidence |
| --- | --- | --- | --- |
| Firewalls | Internet-facing services should be restricted to necessary and approved access. | `direct_cloud` for IaaS/PaaS network rules. | NSG rules, public IP exposure, storage endpoints, exposed admin ports. |
| Firewalls | Administrative interfaces should not be reachable from the internet unless protected. | `direct_cloud` for Azure network exposure; `inferred_cloud` for MFA/allow-list context. | `NET-001`, `NET-002`, `IAM-001`, NSG rule sources, public inbound ports. |
| Firewalls | Inbound firewall rules should be approved, documented, and removed when no longer needed. | `policy_required` with partial cloud support. | Rule age, tags, naming, policy assignments can support review but not prove approval. |
| Firewalls | Software firewalls on user devices used on untrusted networks. | `endpoint_required`. | Requires Intune, Defender for Endpoint, local firewall inventory, or MDM. |
| Secure configuration | Default or guessable credentials should be removed or changed. | `inferred_cloud` for some cloud identities; `endpoint_required` for devices. | Entra roles, privileged accounts, service principals, VM login settings; endpoint state unavailable. |
| Secure configuration | Unnecessary accounts, applications, services, and auto-run features should be removed or disabled. | Mixed: `direct_cloud` for cloud identities/resources; `endpoint_required` for local apps/services. | Disabled/stale service principals, unused resources, VM extension inventory where available. |
| Secure configuration | Device unlock/password configuration should meet CE expectations. | `endpoint_required`. | Requires MDM/Intune/Jamf/local device policy evidence. |
| Secure configuration | Cloud services should be configured securely under shared responsibility. | `inferred_cloud`. | Azure configuration posture, provider evidence contracts, policy assignments, public access settings. |
| Security update management | Supported software must be kept updated. | `inferred_cloud` for Azure VMs; `endpoint_required` for user devices. | VM patch assessment, Defender recommendations, update compliance if available. |
| Security update management | High/critical updates should be applied within the required period. | `inferred_cloud` for managed workloads with patch telemetry; otherwise `endpoint_required`. | Native security recommendations, VM patch state, Defender for Cloud assessment findings. |
| Security update management | Unsupported software should be removed or segregated. | `inferred_cloud` for VM images/resources; `endpoint_required` for devices. | VM image metadata, Defender findings, asset inventory. |
| User access control | Accounts should be assigned to authorised individuals only. | `inferred_cloud`; `manual_required` for authorisation basis. | User/service principal inventory, privileged assignment counts, stale identities. |
| User access control | Users should have only the access needed for their role. | `direct_cloud` for cloud RBAC overprivilege signals; `manual_required` for role/business justification. | `IAM-002`, privileged role assignments, duplicated privileged principals. |
| User access control | Privileged accounts should be separately managed and reviewed. | `inferred_cloud`; review age may be `policy_required` unless access review telemetry exists. | RBAC assignments, Entra access review evidence if added later. |
| User access control | MFA should protect cloud services and privileged access. | `direct_cloud` if Graph permissions allow CA/MFA evidence; otherwise `not_observable` with IAM caveat. | Conditional Access policies, credential registration details, `IAM-001`, `IAM-005`. |
| User access control | Password-based authentication controls. | `inferred_cloud` for Entra/password policies; `endpoint_required` for local device accounts. | Entra policy evidence if Graph path is added; current collector partial. |
| Malware protection | Anti-malware should be active and updated on relevant devices. | `inferred_cloud` for cloud workloads; `endpoint_required` for laptops/desktops/mobile. | Defender coverage ratio, endpoint protection coverage, VM extensions. |
| Malware protection | Malware execution should be prevented or restricted. | `endpoint_required` unless using cloud workload protection evidence. | Requires Defender for Endpoint, Intune app control, allow-list policy inventory. |
| Malware protection | Application allow-listing or sandboxing options. | `endpoint_required` for devices; `inferred_cloud` for managed cloud workloads only. | MDM/EDR integration needed for meaningful coverage. |

## Draft Question-Level Annotation Template

Use this template for each IASME question after licence terms are checked.

```text
question_id:
ce_version: Danzell 16.2 / Requirements v3.3
pillar:
short_paraphrase:
asset_scope:
answer_type: yes_no | free_text | multi_select | scope_statement
evidence_class: direct_cloud | inferred_cloud | endpoint_required | policy_required | manual_required | not_observable
cloud_provider_paths:
  azure:
    api_or_cli:
    current_cris_sme_signal:
    planned_signal:
  aws:
    api_or_cli:
    current_cris_sme_signal:
    planned_signal:
  gcp:
    api_or_cli:
    current_cris_sme_signal:
    planned_signal:
supporting_control_ids:
proposed_answer_rule:
human_review_required: true
liability_caveat:
paper_notes:
```

## Implementation Shape

Do not begin with a full generated questionnaire. Begin with the coverage map.

Proposed files:

```text
data/ce_question_mapping.json
src/cris_sme/engine/ce_questionnaire.py
src/cris_sme/reporting/ce_questionnaire_report.py
tests/test_ce_questionnaire.py
outputs/reports/cris_sme_ce_self_assessment.json
outputs/reports/cris_sme_ce_self_assessment.html
```

Suggested JSON shape:

```json
{
  "question_id": "CE-FW-001",
  "ce_version": "Danzell 16.2 / Requirements v3.3",
  "pillar": "Firewalls",
  "short_paraphrase": "Internet-facing administrative access is restricted and protected.",
  "evidence_class": "direct_cloud",
  "supporting_control_ids": ["NET-001", "NET-002", "IAM-001"],
  "provider_paths": {
    "azure": ["network security group rules", "public IP inventory", "conditional access policy visibility"]
  },
  "human_review_required": true,
  "licence_note": "Paraphrased mapping; does not reproduce IASME question text."
}
```

## Evaluation Plan

Evaluation environments:

1. CRIS-SME mock baseline.
2. Authorized Azure lab / AzureGoat-style vulnerable lab.
3. One real SME or SME-like tenant, ideally UK-based.

Metrics:

- question coverage by evidence class
- agreement with expert/manual CE answer draft
- evidence retrieval time for cloud-observable questions
- number of generated caveats accepted by reviewer
- number of unsafe auto-answers prevented by evidence-class labelling
- proportion of questions requiring endpoint/MDM/EDR integration

Time-saving should be measured carefully. Prefer evidence retrieval time over total questionnaire completion time unless a controlled user study is available.

## Competitor / Related Tool Checks

These must be checked before any novelty claim is made:

- Microsoft Defender for Cloud regulatory compliance Cyber Essentials support.
- IASME portal and readiness tool.
- JumpCloud Cyber Essentials readiness material.
- Axonius compliance mapping.
- ConnectWise / Datto / NinjaRMM MSP compliance helper tooling.
- UK consultancies or assessors with CE helper products.
- Open-source CSPM tools such as Prowler, ScoutSuite, Steampipe, and CloudQuery.

Working novelty statement:

> To our knowledge, existing tools provide readiness guidance, compliance-control mapping, or resource-level compliance assessments, but do not generate a question-level Cyber Essentials self-assessment answer pack from live cloud telemetry with explicit evidence-sufficiency labels and human-verification boundaries.

## Immediate Next Steps

1. Download the current IASME question set through the official NCSC/IASME route.
2. Confirm whether the question text can be used in academic notes, private repo files, and public open-source mappings.
3. Review `data/ce_question_mapping.json` against the official Danzell question set using paraphrases and stable local IDs.
4. Re-count evidence classes after expert review.
5. Build the first answer-pack generator only after the mapping is reviewed.
