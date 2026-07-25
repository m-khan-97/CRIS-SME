# CRIS-SME Cyber Essentials Paper Tables

- Question set: `Danzell` version `16.2`
- Requirements version: `3.3`
- Total mapped entries: `106`
- Technical-control entries: `62`
- Cloud-supported entries: `28` (`26.42%`)
- Technical cloud-supported entries: `22` (`35.48%`)
- Human reviewer agreement: `0` of `0` (`0.0%`)
- AI-assisted draft acceptance: `0` of `0` (`0.0%`)

## Table 1. CE Question Observability By Evidence Class

| Count | Label | Rate |
| --- | --- | --- |
| 5 | direct_cloud | 4.72 |
| 24 | endpoint_required | 22.64 |
| 23 | inferred_cloud | 21.7 |
| 35 | manual_required | 33.02 |
| 19 | policy_required | 17.92 |

## Table 2. Technical-Question Observability

| Count | Label | Rate |
| --- | --- | --- |
| 5 | direct_cloud | 8.06 |
| 21 | endpoint_required | 33.87 |
| 17 | inferred_cloud | 27.42 |
| 1 | manual_required | 1.61 |
| 18 | policy_required | 29.03 |

## Table 3. Evidence Gap Taxonomy

| Count | Description | Evidence Class | Rate | Sample Question Ids |
| --- | --- | --- | --- | --- |
| 24 | Endpoint, MDM, EDR, patch, or local device evidence required. | endpoint_required | 22.64 | A2.6; A2.6.1; A2.8; A4.1.1; A4.1.2; A5.1; A5.3; A5.8 |
| 35 | Applicant scoping, company context, or final attestation required. | manual_required | 33.02 | A1.1; A1.2; A1.3; A1.4; A1.5; A1.5.1; A1.6; A1.6.1 |
| 0 | Required signal is outside current CRIS-SME observable evidence paths. | not_observable | 0.0 |  |
| 19 | Policy, process, approval, or business-need evidence required. | policy_required | 17.92 | A1.16; A4.2; A4.2.1; A4.3; A4.4; A4.5; A4.6; A4.8 |

## Table 4. Review Outcomes

| Count | Label | Rate |
| --- | --- | --- |
| 106 | pending | 100.0 |

## Table 5. Proposed CE Answers

| Count | Label | Rate |
| --- | --- | --- |
| 78 | Cannot determine | 73.58 |
| 24 | No | 22.64 |
| 4 | Yes | 3.77 |

## Table 6. Top Controls Contributing To CE Answer Failures

| Affected Question Count | Control Id | Max Linked Score | Sample Finding Titles |
| --- | --- | --- | --- |
| 9 | IAM-001 | 67.97 | Privileged role assignments without MFA enforcement |
| 6 | NET-002 | 44.71 | Network security group rules are broader than expected |
| 5 | NET-001 | 72.12 | Administrative services are exposed to the public internet |
| 4 | CMP-001 | 42.69 | Critical workloads remain unpatched beyond acceptable risk tolerance |
| 3 | IAM-003 | 23.34 | Stale service principals or credentials require review |
| 3 | IAM-005 | 4.57 | Identity governance observability is partial for this assessment scope |
| 2 | DATA-001 | 48.35 | Public storage access increases data exposure risk |
| 1 | CMP-003 | 38.49 | Workload hardening baseline coverage is incomplete |
| 1 | GOV-003 | 33.88 | Policy assignment coverage is below the baseline governance threshold |
| 1 | GOV-004 | 17.87 | Orphaned resources increase governance and cost hygiene risk |

## Table 7. Section-Level Coverage

| Cloud Supported Count | Cloud Supported Rate | Question Count | Reviewed Count | Section |
| --- | --- | --- | --- | --- |
| 0 | 0.0 | 2 | 0 | certificates |
| 4 | 28.57 | 14 | 0 | firewalls |
| 0 | 0.0 | 3 | 0 | insurance |
| 0 | 0.0 | 5 | 0 | malware_protection |
| 6 | 33.33 | 18 | 0 | scope_of_assessment |
| 4 | 40.0 | 10 | 0 | secure_configuration |
| 3 | 18.75 | 16 | 0 | security_update_management |
| 11 | 64.71 | 17 | 0 | user_access_control |
| 0 | 0.0 | 21 | 0 | your_company |

## Reproducibility Notes

- Human agreement rate compares proposed_answer to non-AI reviewer final_answer and excludes pending entries, needs-evidence requests, and AI-assisted pilot decisions.
- AI-assisted pilot decisions are reported as draft acceptance, not reviewer agreement.
- Cloud observability counts direct_cloud and inferred_cloud evidence classes only.
- A proposed Yes means no mapped CRIS-SME cloud-control-plane risk was observed; it is not proof that every implementation path for the CE requirement is satisfied.
- Endpoint, policy, manual, and not-observable items are evidence gaps, not compliance failures by themselves.
- Metrics are derived from CRIS-SME artifacts and reviewer ledger states; they do not certify Cyber Essentials compliance.
- No impact. CE evaluation metrics are downstream measurements and never change CRIS-SME deterministic findings, priorities, or scores.
