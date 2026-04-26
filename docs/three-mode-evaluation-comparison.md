# Three-Mode Evaluation Comparison

> Status: paper-facing comparison draft.  
> Contains curated historical values and should be refreshed when using new run snapshots.

This document provides a paper-ready comparison of the three current CRIS-SME evaluation modes:

- synthetic SME baseline
- live Azure case study
- AzureGoat-derived vulnerable-lab track

Its purpose is to make the evaluation story easy to reuse in the manuscript, slides, posters, or proposal materials with all three modes treated as equal first-class evidence.

## Table 1. Evaluation Mode Summary

| Mode | Evidence Class | Authorization Basis | Purpose | Strength | Limitation |
| --- | --- | --- | --- | --- | --- |
| Synthetic SME baseline | Synthetic profiles | `synthetic_dataset` | Controlled baseline and regression testing | Fully reproducible | Not a real cloud estate |
| Live Azure case study | Production-adjacent live tenant | `authorized_tenant_access` | Real-cloud feasibility and Azure-native comparison | Empirical live evidence | One live subscription |
| AzureGoat vulnerable lab | Intentionally vulnerable Azure lab | `intentionally_vulnerable_lab` | Control stress testing in an explicitly allowed environment | High-variance lawful stress track | Constrained deployment variant |

## Table 2. Headline Outcome Comparison

| Metric | Synthetic Baseline | Live Azure Case Study | AzureGoat Vulnerable Lab |
| --- | ---: | ---: | ---: |
| Overall risk score | 39.84 | 32.79 | 32.79 |
| Evaluated profiles | 3 | 1 | 1 |
| Generated findings | 50 | 19 | 18 |
| Non-compliant findings | 49 | 18 | 18 |
| Collector mode | `mock` | `azure` | `azure` |

## Table 3. Category Score Comparison

| Category | Synthetic Baseline | Live Azure Case Study | AzureGoat Vulnerable Lab |
| --- | ---: | ---: | ---: |
| IAM | 34.00 | 14.78 | 14.78 |
| Network | 51.62 | 38.02 | 38.02 |
| Data | 42.05 | 48.65 | 48.65 |
| Monitoring/Logging | 37.61 | 36.38 | 36.38 |
| Compute/Workloads | 42.69 | 38.29 | 38.29 |
| Cost/Governance Hygiene | 26.91 | 24.80 | 24.80 |

## Interpretation

- The synthetic baseline remains the broadest and most intentionally stressed dataset, which is why it still produces the highest overall score and the largest number of findings.
- The live Azure case study contributes the real authenticated-tenant lens and Azure-native comparison hooks.
- The AzureGoat track contributes the explicitly vulnerable, fully authorized stress-test lens without relying on arbitrary public infrastructure.
- The latest live Azure and AzureGoat snapshots currently share the same overall score, which is useful because it shows that provenance and evidence class still matter even when headline totals converge.

## Recommended Use in the Paper

Use this comparison in three places:

1. In the evaluation-method section to justify the three-mode design.
2. In the results section as the main headline comparison table.
3. In the discussion section to explain how controlled, live, and vulnerable-lab evidence each illuminate different aspects of SME cloud governance risk.

## Disclosure Note

The current AzureGoat run was collected from a constrained deployment variant rather than a fully stock AzureGoat deployment. Region policy, Automation Account restrictions, Basic public-IP incompatibility, and regional VM-capacity shortages required adaptation. This should be disclosed in the threats-to-validity discussion rather than hidden.
