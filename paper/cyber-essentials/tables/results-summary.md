# CRIS-SME Cyber Essentials Paper Tables

## Table 1. Question Observability

| Evidence class | Count | Rate |
| --- | ---: | ---: |
| direct_cloud | 5 | 4.72% |
| inferred_cloud | 23 | 21.70% |
| endpoint_required | 24 | 22.64% |
| policy_required | 19 | 17.92% |
| manual_required | 35 | 33.02% |

## Table 2. Technical-Control Observability

| Evidence class | Count | Rate |
| --- | ---: | ---: |
| direct_cloud | 5 | 8.06% |
| inferred_cloud | 17 | 27.42% |
| endpoint_required | 21 | 33.87% |
| policy_required | 18 | 29.03% |
| manual_required | 1 | 1.61% |

## Table 3. Controlled Azure Vulnerable-Lab Category Scores

| Category | Score |
| --- | ---: |
| IAM | 32.51 |
| Network | 58.42 |
| Data | 41.74 |
| Monitoring/Logging | 36.38 |
| Compute/Workloads | 38.29 |
| Cost/Governance Hygiene | 27.11 |

## Table 4. Proposed Cyber Essentials Answers

| Proposed answer | Count |
| --- | ---: |
| No | 23 |
| Yes | 5 |
| Cannot determine | 78 |

## Table 5. Review Metrics

Note: AI-assisted draft acceptance and human agreement are separate processes on the same 28 cloud-supported entries.
The AI draft accepted all 23 proposed-No rows (conservative policy) and flagged all 5 proposed-Yes rows (needs-evidence policy).
The human reviewer confirmed those same 23 No rows and confirmed the 5 flags. Zero overrides were recorded.

| Metric | Value | Notes |
| --- | ---: | --- |
| Cloud-supported entries reviewed | 28 | All direct_cloud and inferred_cloud entries |
| Revalidation rows cross-checked | 8 | Stale rows from earlier review pass; all resolved as accepted/No |
| **AI-assisted draft** | | Separate pre-review; not counted as human agreement |
| AI draft accepted (conservative No) | 23 | All proposed-No rows; direct_cloud + inferred_cloud with linked findings |
| AI draft needs-evidence (proposed Yes) | 5 | All proposed-Yes rows flagged; absence-of-finding is insufficient |
| AI draft pending (non-cloud) | 78 | Endpoint, policy, manual entries excluded from draft scope |
| **Human review** | | Author self-assessment; see Threats to Validity |
| Human reviewed (agreement-evaluable) | 23 | Same 23 rows as AI-draft-accepted; all proposed-No |
| Human accepted | 23 | All 23 match CRIS-SME proposed answer |
| Human overrides | 0 | No disagreements recorded |
| Human needs-evidence confirmed | 5 | Reviewer confirmed all 5 proposed-Yes flags |
| **Agreement summary** | | |
| Agreement evaluable count | 23 | Proposed-No rows only; proposed-Yes excluded from denominator |
| Agreement count | 23 | All 23 accepted rows matched CRIS-SME proposed answer |
| Agreement rate | 23/23 | Written as fraction; 100.0% in machine output |
| External human cross-check | Complete | Author self-assessment; independent assessor review is future work |

## Table 6. Top Controls Contributing to Proposed `No` Answers

| Control | Affected entries | Max linked score |
| --- | ---: | ---: |
| IAM-001 | 9 | 67.97 |
| NET-002 | 6 | 44.71 |
| NET-001 | 5 | 72.12 |
| IAM-002 | 5 | 24.98 |
| IAM-005 | 3 | 4.57 |
| DATA-001 | 2 | 48.35 |
| CMP-003 | 1 | 38.49 |
| GOV-003 | 1 | 33.88 |
