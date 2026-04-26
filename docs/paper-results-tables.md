# Paper Results Tables

> Status: manuscript support artifact.  
> Table values may be frozen to specific archival snapshots and are not guaranteed to match current local outputs unless regenerated.

This document consolidates the current CRIS-SME results into a paper-friendly form. It is intended to support the evaluation and results sections of the first manuscript.

The tables below deliberately separate and then recombine:

- the current synthetic SME baseline
- the latest live Azure case-study baseline used for research discussion
- the current AzureGoat-derived vulnerable-lab stress track

## Table 1. Assessment Modes Used in the Current Study

| Mode | Source | Purpose | Current Role in Paper |
| --- | --- | --- | --- |
| Synthetic / mock | `data/synthetic_sme_profiles.json` | Repeatable control and scoring validation | Equal first-class evaluation mode |
| Live Azure | Archived Azure-backed assessment snapshot | Real-cloud feasibility with authorized tenant evidence | Equal first-class evaluation mode |
| AzureGoat vulnerable lab | Constrained AzureGoat deployment in an authorized subscription | Control-stress test with intentionally vulnerable resources | Equal first-class evaluation mode |

## Table 2. Headline Outcome Comparison Across the Three Modes

| Metric | Synthetic Baseline | Live Azure Case Study | AzureGoat Vulnerable Lab |
| --- | ---: | ---: | ---: |
| Overall risk score | 39.84 | 32.79 | 32.79 |
| Evaluated profiles | 3 | 1 | 1 |
| Generated findings | 50 | 19 | 18 |
| Non-compliant findings | 49 | 18 | 18 |
| Collector mode | mock | azure | azure |
| Dataset source type | synthetic_dataset | live_real | vulnerable_lab |
| Authorization basis | synthetic_dataset | authorized_tenant_access | intentionally_vulnerable_lab |

Interpretation:

- Synthetic data currently produces the broadest and most numerous finding set because it covers multiple deliberately stressed SME profiles.
- The live Azure run contributes real subscription evidence and Azure-native comparison hooks.
- The AzureGoat-derived run contributes a lawful vulnerable-lab stress track that reaches different control paths from the live tenant.
- Together, the three modes form the main evaluation story rather than a primary-plus-secondary hierarchy.

## Table 3. Category Score Comparison

| Category | Synthetic Baseline | Live Azure Case Study | AzureGoat Vulnerable Lab |
| --- | ---: | ---: | ---: |
| IAM | 34.00 | 14.78 | 14.78 |
| Network | 51.62 | 38.02 | 38.02 |
| Data | 42.05 | 48.65 | 48.65 |
| Monitoring/Logging | 37.61 | 36.38 | 36.38 |
| Compute/Workloads | 42.69 | 38.29 | 38.29 |
| Cost/Governance Hygiene | 26.91 | 24.80 | 24.80 |

Interpretation:

- Network remains a dominant risk domain across all three settings.
- IAM is substantially lower in both Azure-backed runs than in the synthetic baseline, which suggests the synthetic baseline still stresses identity governance more aggressively than the current observed Azure environments.
- Data risk is highest in the vulnerable-lab track, showing that the three-mode framing surfaces domain-specific variation rather than only overall-score variation.

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

## Table 6. Synthetic Baseline Top Risks

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

## Table 7. Budget-Aware Remediation Packs in the Synthetic Baseline

| Budget Profile | Monthly Cap (GBP) | Actions | Cumulative Risk Covered | Average Value Score |
| --- | ---: | ---: | ---: | ---: |
| Free fixes this week | 0 | 5 | 298.54 | 59.71 |
| Under GBP200 per month | 200 | 7 | 396.12 | 56.59 |
| Under GBP750 per month | 750 | 10 | 585.89 | 53.03 |

Interpretation:

- Even the zero-cost pack covers substantial cumulative risk, which supports the paper claim that CRIS-SME is designed for budget-constrained SMEs.
- This is a stronger practical output than severity-only ranking because it ties remediation order to affordability.

## Table 8. UK-Oriented Assurance Outputs in the Current Framework

| Output | Current Status |
| --- | --- |
| UK regulatory mapping | Implemented |
| Cyber Essentials readiness | Implemented |
| Cyber insurance evidence pack | Implemented |
| Executive pack | Implemented |
| Budget-aware remediation | Implemented |

Interpretation:

- These outputs are central to the paper argument that CRIS-SME is not only a scoring engine, but an SME-facing governance system.

## Table 9. Recommended Figures for the Paper

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
3. Use Table 7 in the actionability discussion.
4. Use the figure set above for visual support.
5. Move lower-priority detailed finding lists into the appendix.

## Data Provenance

These tables were prepared from:

- the synthetic baseline report lineage represented in `outputs/reports/history/`
- the live Azure historical snapshot `outputs/reports/history/cris_sme_report_20260422T123539Z.json`
- the AzureGoat vulnerable-lab run collected on `2026-04-22`

If newer live snapshots are used in the paper, this document should be refreshed to keep the manuscript numerically consistent.
