# Paper Results Tables

> Status: manuscript support artifact.  
> Table values may be frozen to specific archival snapshots and are not guaranteed to match current local outputs unless regenerated.

This document consolidates the current CRIS-SME results into a paper-friendly form. It is intended to support the evaluation and results sections of the first manuscript.

The tables below deliberately separate:

- the current synthetic SME baseline
- the latest live Azure case-study baseline used for research discussion
- the current AzureGoat-derived vulnerable-lab stress track

## Table 1. Assessment Modes Used in the Current Study

| Mode | Source | Purpose | Current Role in Paper |
| --- | --- | --- | --- |
| Synthetic / mock | `data/synthetic_sme_profiles.json` | Repeatable control and scoring validation | Baseline for controlled comparison |
| Live Azure | Archived Azure-backed assessment snapshot | Case-study evaluation with real cloud evidence | Main empirical case study |
| AzureGoat vulnerable lab | Constrained AzureGoat deployment in an authorized subscription | Control-stress test with intentionally vulnerable resources | Secondary empirical stress track |

## Table 2. Headline Outcome Comparison: Synthetic Baseline vs Live Azure

| Metric | Synthetic Baseline | Live Azure Case Study |
| --- | ---: | ---: |
| Overall risk score | 39.84 | 33.23 |
| Evaluated profiles | 3 | 1 |
| Generated findings | 50 | 19 |
| Non-compliant findings | 49 | 18 |
| Collector mode | mock | azure |

Notes:

- Synthetic data currently produces a broader and more numerous finding set because it covers multiple deliberately stressed SME profiles.
- The live Azure case study is narrower but grounded in real subscription evidence.

## Table 2a. AzureGoat Vulnerable-Lab Snapshot

| Metric | AzureGoat Lab Track |
| --- | ---: |
| Overall risk score | 32.79 |
| Evaluated profiles | 1 |
| Non-compliant findings | 18 |
| Collector mode | azure |
| Dataset source type | vulnerable_lab |
| Authorization basis | intentionally_vulnerable_lab |

Interpretation:

- The AzureGoat-derived run gives CRIS-SME a third evaluation mode between synthetic profiles and the live production-adjacent case study.
- This track is especially useful for stressing exposed storage, function-app, network, and data-governance controls in an authorized environment.
- The current AzureGoat snapshot was collected from a constrained deployment variant because subscription policy and regional capacity prevented a full stock-lab rollout.

## Table 3. Category Score Comparison

| Category | Synthetic Baseline | Live Azure Case Study | Delta (Live - Synthetic) |
| --- | ---: | ---: | ---: |
| IAM | 34.00 | 14.78 | -19.22 |
| Network | 51.62 | 47.59 | -4.03 |
| Data | 42.05 | 39.75 | -2.30 |
| Monitoring/Logging | 37.61 | 36.38 | -1.23 |
| Compute/Workloads | 42.69 | 39.02 | -3.67 |
| Cost/Governance Hygiene | 26.91 | 27.11 | +0.20 |

Interpretation:

- Network remains the highest-risk domain in both settings.
- IAM is substantially lower in the live case-study snapshot than in the synthetic baseline, which suggests the synthetic baseline still stresses identity governance more aggressively than the current live tenant.
- Governance hygiene is broadly comparable across both modes.

## Table 4. Native Recommendation Validation in the Live Azure Case Study

| Metric | Value |
| --- | ---: |
| Framework | Microsoft Defender for Cloud |
| Controls mapped | 7 |
| Native unhealthy recommendations | 10 |
| Agreement count | 2 |
| CRIS-only count | 4 |
| Native-only count | 0 |

Interpretation:

- CRIS-SME and Defender aligned on two mapped control areas in the reference live snapshot.
- Four mapped controls were CRIS-only, which supports the argument that CRIS-SME adds distinct governance interpretation rather than merely reproducing Azure-native output.
- No mapped control was native-only in this reference live comparison.

## Table 5. Live Azure Control-Level Agreement Snapshot

| Control | Comparison Status | CRIS-SME Score | Native Recommendation Count |
| --- | --- | ---: | ---: |
| IAM-002 | agreement | 24.98 | 1 |
| NET-002 | agreement | 44.71 | 3 |
| NET-001 | cris_only | 50.48 | 0 |
| CMP-002 | cris_only | 39.53 | 0 |
| CMP-003 | cris_only | 38.49 | 0 |
| MON-003 | cris_only | 36.94 | 0 |
| CMP-001 | clear | N/A | 0 |

Interpretation:

- Agreement is strongest in subscription ownership hygiene and permissive network exposure.
- CRIS-SME identifies several workload and monitoring governance concerns that were not surfaced in the visible unhealthy Defender recommendations of this snapshot.

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

- the current synthetic report in `outputs/reports/cris_sme_report.json`
- the live Azure historical snapshot `outputs/reports/history/cris_sme_report_20260418T004604Z.json`
- the AzureGoat vulnerable-lab run collected on `2026-04-22`

If newer live snapshots are used in the paper, this document should be refreshed to keep the manuscript numerically consistent.
