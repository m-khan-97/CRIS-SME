# Paper Results Tables

> Status: manuscript support artifact.  
> Table values may be frozen to specific archival snapshots and are not guaranteed to match current local outputs unless regenerated.

This document consolidates the current CRIS-SME results into a paper-friendly form. It is intended to support the evaluation and results sections of the first manuscript.

The tables below deliberately separate and then recombine:

- the current synthetic SME baseline
- the latest live Azure case-study baseline used for research discussion
- the current controlled Azure vulnerable-lab stress track

## Table 1. Assessment Modes Used in the Current Study

| Mode | Source | Purpose | Current Role in Paper |
| --- | --- | --- | --- |
| Synthetic / mock | `data/synthetic_sme_profiles.json` | Repeatable control and scoring validation | Equal first-class evaluation mode |
| Live Azure | Archived Azure-backed assessment snapshot | Real-cloud feasibility with authorized tenant evidence | Equal first-class evaluation mode |
| Controlled Azure vulnerable lab | Small authorized lab with public admin NSG rules and public storage evidence | Control-stress test with intentionally vulnerable cloud-control-plane resources | Equal first-class evaluation mode |

## Table 2. Headline Outcome Comparison Across the Three Modes

| Metric | Synthetic Baseline | Live Azure Case Study | Controlled Azure Vulnerable Lab |
| --- | ---: | ---: | ---: |
| Overall risk score | 39.84 | 27.81 | 40.16 |
| Evaluated profiles | 3 | 1 | 1 |
| Generated findings | 50 | 15 | 18 |
| Non-compliant findings | 49 | 15 | 18 |
| Collector mode | mock | azure | azure |
| Dataset source type | synthetic_dataset | live_subscription | vulnerable_lab |
| Authorization basis | synthetic_dataset | authorized_subscription_owner | intentionally_vulnerable_lab |

Interpretation:

- Synthetic data currently produces the broadest and most numerous finding set because it covers multiple deliberately stressed SME profiles.
- The live Azure run contributes real subscription evidence and Azure-native comparison hooks.
- The controlled Azure vulnerable-lab run contributes a lawful stress track that reaches different control paths from the live tenant.
- Together, the three modes form the main evaluation story rather than a primary-plus-secondary hierarchy.

## Table 3. Category Score Comparison

| Category | Synthetic Baseline | Live Azure Case Study | Controlled Azure Vulnerable Lab |
| --- | ---: | ---: | ---: |
| IAM | 34.00 | 32.51 | 32.51 |
| Network | 51.62 | 0.00 | 58.42 |
| Data | 42.05 | 38.44 | 41.74 |
| Monitoring/Logging | 37.61 | 36.38 | 36.38 |
| Compute/Workloads | 42.69 | 38.29 | 38.29 |
| Cost/Governance Hygiene | 26.91 | 27.11 | 27.11 |

Interpretation:

- Network is intentionally low in the clean live Azure run and high in the controlled vulnerable lab, which gives the paper a useful stress-test contrast.
- Data risk rises in the controlled lab because the empty storage account was configured with public network/blob access signals.
- IAM is consistent across the two Azure runs because the subscription-level identity evidence boundary is shared.

## Table 4. Native Recommendation Validation in the Live Azure Case Study

| Metric | Value |
| --- | ---: |
| Framework | Microsoft Defender for Cloud |
| Controls mapped | 7 |
| Native unhealthy recommendations | 0 |
| Agreement count | 0 |
| CRIS-only count | 6 |
| Native-only count | 0 |

Interpretation:

- In the latest live snapshot, no mapped control was visible as an active unhealthy Defender recommendation.
- Six mapped controls were CRIS-only, which supports the argument that CRIS-SME adds distinct governance interpretation rather than merely reproducing Azure-native output.
- No mapped control was native-only in this reference live comparison.

## Table 5. Live Azure Control-Level Agreement Snapshot

| Control | Comparison Status | CRIS-SME Score | Native Recommendation Count |
| --- | --- | ---: | ---: |
| IAM-002 | cris_only | 24.98 | 0 |
| NET-002 | cris_only | 25.55 | 0 |
| NET-001 | cris_only | 50.48 | 0 |
| CMP-002 | cris_only | 39.53 | 0 |
| CMP-003 | cris_only | 38.49 | 0 |
| MON-003 | cris_only | 36.94 | 0 |
| CMP-001 | clear | N/A | 0 |

Interpretation:

- The latest live snapshot is currently a CRIS-dominant comparison rather than an agreement-heavy one.
- CRIS-SME identifies several workload, network, and monitoring governance concerns that were not surfaced in the visible unhealthy Defender recommendations of this snapshot.

## Table 6. Controlled Azure Vulnerable-Lab Top Risks

| Control | Finding | Priority | Score | Evidence |
| --- | --- | --- | ---: | --- |
| NET-001 | Administrative services are exposed to the public internet | High | 72.12 | 1 RDP and 1 SSH exposure signal |
| IAM-001 | Privileged role assignments without MFA enforcement | High | 67.97 | Conditional Access not observable and treated as unmet |
| DATA-001 | Public storage access increases data exposure risk | Planned | 48.35 | 1 storage asset allows public access |
| NET-002 | Network security group rules are broader than expected | Planned | 44.71 | 2 permissive NSG rules |

Interpretation:

- The controlled lab intentionally triggered network and storage controls without attaching a reachable VM to the public administrative rules.
- This makes the lab suitable for a lawful stress test and safer than deploying a fully reachable vulnerable workload.

## Table 7. Controlled Azure Lab Cyber Essentials Outputs

| Metric | Value |
| --- | ---: |
| Mapped CE entries | 106 |
| Technical-control entries | 62 |
| Cloud-supported entries | 28 |
| Cloud-supported rate | 26.42% |
| Technical cloud-supported entries | 22 |
| Technical cloud-supported rate | 35.48% |
| Proposed Yes answers | 5 |
| Proposed No answers | 23 |
| Cannot determine answers | 78 |
| AI-assisted draft accepted | 23 |
| AI-assisted draft needs evidence | 5 |
| Pending review entries | 78 |

Interpretation:

- The lab gives the CE paper a concrete vulnerable-cloud case study with question-level answer impact.
- The AI-assisted draft review values are pilot workflow measurements, not independent human assessor agreement.
- Proposed `Yes` answers mean no mapped cloud-control-plane issue was observed; they should not be described as proof of CE compliance without human corroboration.

## Table 8. Synthetic Baseline Top Risks

| Control | Category | Priority | Score | Cost Tier | Value Score |
| --- | --- | --- | ---: | --- | ---: |
| NET-001 | Network | Immediate | 87.90 | medium | 47.51 |
| IAM-001 | IAM | Immediate | 82.84 | free | 82.84 |
| CMP-001 | Compute/Workloads | High | 74.32 | medium | 40.17 |
| DATA-001 | Data | High | 58.93 | free | 58.93 |
| NET-003 | Network | High | 58.47 | low | 43.31 |

Interpretation:

- The synthetic baseline continues to emphasize a mix of external exposure, privileged identity risk, and workload patching gaps.
- Budget-aware value scores show that not all high-risk issues are equally attractive for constrained remediation.

## Table 9. Budget-Aware Remediation Packs in the Synthetic Baseline

| Budget Profile | Monthly Cap (GBP) | Actions | Cumulative Risk Covered | Average Value Score |
| --- | ---: | ---: | ---: | ---: |
| Free fixes this week | 0 | 5 | 298.54 | 59.71 |
| Under GBP200 per month | 200 | 7 | 396.12 | 56.59 |
| Under GBP750 per month | 750 | 10 | 585.89 | 53.03 |

Interpretation:

- Even the zero-cost pack covers substantial cumulative risk, which supports the paper claim that CRIS-SME is designed for budget-constrained SMEs.
- This is a stronger practical output than severity-only ranking because it ties remediation order to affordability.

## Table 10. UK-Oriented Assurance Outputs in the Current Framework

| Output | Current Status |
| --- | --- |
| UK regulatory mapping | Implemented |
| Cyber Essentials readiness | Implemented |
| Cyber insurance evidence pack | Implemented |
| Executive pack | Implemented |
| Budget-aware remediation | Implemented |

Interpretation:

- These outputs are central to the paper argument that CRIS-SME is not only a scoring engine, but an SME-facing governance system.

## Table 11. Recommended Figures for the Paper

| Figure | Current Artifact |
| --- | --- |
| Category score chart | `outputs/figures/live_category_scores.svg` |
| Priority distribution chart | `outputs/figures/live_priority_distribution.svg` |
| Risk trend chart | `outputs/figures/risk_trend.svg` |
| Run comparison chart | `outputs/figures/run_comparison.svg` |

## Suggested Use in the Manuscript

The cleanest paper structure is:

1. Use Table 2 and Table 3 in the main results section.
2. Use Table 4 and Table 5 in the validation/comparison section.
3. Use Table 7 for the CE paper and Table 9 in the actionability discussion.
4. Use the figure set above for visual support.
5. Move lower-priority detailed finding lists into the appendix.

## Data Provenance

These tables were prepared from:

- the synthetic baseline report lineage represented in `outputs/reports/history/`
- the latest live Azure run represented in `outputs/reports/cris_sme_report.json`
- the controlled Azure vulnerable-lab run collected on `2026-05-07`, documented in `docs/research/controlled-azure-lab-run-2026-05-07.md`

If newer live snapshots are used in the paper, this document should be refreshed to keep the manuscript numerically consistent.
