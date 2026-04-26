# Live Azure Case Study

> Status: historical reference snapshot.  
> This document is paper-facing and may include frozen values from specific archived runs that are not guaranteed to match the latest local output.

This document captures a real CRIS-SME assessment run against an authenticated Azure subscription. Its purpose is to preserve the live-Azure branch of the current three-mode evaluation rather than to position the live run as the sole primary paper case study.

## Purpose

This case study supports three goals inside the broader three-mode evaluation:

- demonstrate that CRIS-SME now operates beyond mock data alone
- show how deterministic scoring and control evaluation behave on a real tenant
- provide reusable research-facing outputs for demos, posters, abstracts, and future papers

The case study should be read as one evidence class within the broader evaluation design, not as a generalized benchmark of Azure SME risk.

## Assessment Context

Assessment reference snapshot:
- `outputs/reports/history/cris_sme_report_20260422T123539Z.json`

Assessment date:
- April 22, 2026

Collector mode:
- live Azure-backed collection via `CRIS_SME_COLLECTOR=azure`

Active subscription:
- `Azure for Students`

Provider posture model:
- provider-neutral CRIS-SME core with Azure-first collection and normalization

Implemented live evidence domains in this run:
- IAM and Entra-adjacent privileged role evidence
- Network
- Data
- Monitoring and Logging
- Compute and Workloads
- Governance and Cost Hygiene

Current identity boundary:
- privileged role assignments are collected live from the subscription scope
- tenant-wide Entra controls such as Conditional Access remain only partially observable in the current collector scope

## Live Evidence Observed

The latest reference report recorded the following evidence counts:

- `2` privileged assignments
- `1` privileged principal
- `0` visible Entra directory roles for the signed-in assessment identity in the current run
- `0` privileged service principal assignments
- `0` virtual machines
- `2` storage accounts
- `0` SQL servers
- `0` SQL databases counted for the current data evidence path
- `0` activity log alerts
- `2` Logic Apps workflows
- `1` policy assignment
- `0` Linux VMs with password authentication enabled
- `0` VM backup-protected assets

These values were exported into the report provenance section so downstream readers can distinguish what was directly observed from what remains conservative by design.

## Headline Results

The live Azure run produced:

- overall risk score: `32.79/100`
- non-compliant findings: `18`
- evaluated profiles: `1`

Category scores:

- IAM: `14.78`
- Network: `38.02`
- Data: `48.65`
- Monitoring/Logging: `36.38`
- Compute/Workloads: `38.29`
- Cost/Governance Hygiene: `24.80`

Within the three-mode evaluation, these values sit alongside:

- synthetic baseline overall risk: `39.84`
- AzureGoat vulnerable-lab overall risk: `32.79`

That makes this document best used as the live-evidence subsection of the paper rather than as the only headline results section.

## Figure Snapshot

![Live category scores](../outputs/figures/live_category_scores.svg)

![Live priority distribution](../outputs/figures/live_priority_distribution.svg)

![Overall risk trend](../outputs/figures/risk_trend.svg)

![Run comparison](../outputs/figures/run_comparison.svg)

The figures were generated from CRIS-SME JSON report artifacts via [04-live-report-figures.ipynb](../notebooks/04-live-report-figures.ipynb) and the reusable chart exporter in [figure_export.py](../src/cris_sme/reporting/figure_export.py).

The history figures are based on archived report snapshots in [outputs/reports/history](../outputs/reports/history), which now include synthetic, live Azure, and vulnerable-lab runs. The frozen case-study values in this document should be treated as the canonical live Azure reference inside the manuscript's three-mode comparison rather than inferred from whichever report artifact was generated most recently.

## Most Significant Findings

The highest-priority observations in the current live run were:

1. `DATA-001` Public storage access increases data exposure risk
2. `NET-001` Administrative services exposed to the public internet
3. `CMP-002` Endpoint protection coverage is below the expected workload baseline
4. `DATA-004` Key management protections are incomplete for sensitive secrets
5. `CMP-003` Workload hardening baseline coverage is incomplete

IAM-specific observations are now more precise than earlier versions of the case study:

- `IAM-002` identified duplicate privileged access concentration rather than broadly claiming missing MFA
- `IAM-005` explicitly recorded that identity observability is partial for this assessment scope

This is an improvement in research credibility because the framework now distinguishes between directly observed identity risks and identity controls that remain outside the current evidence boundary.

## Identity and Compute Observations

The live IAM and compute analysis is especially useful because it reflects real assets already present in the tenant rather than synthetic assumptions.

Observed identity posture:

- subscription-scoped privileged role assignments were collected successfully
- the current run saw `2` privileged assignments associated with `1` privileged principal
- no role-assigned service principals were present in the observed privileged set
- no Entra directory roles were visible for the signed-in assessment identity in the current run
- Conditional Access was not directly observable within the current tenant permissions and collector scope

Observed compute posture:

- no virtual machines were present in the current live evidence path
- no Recovery Services vaults were present for VM backup coverage
- endpoint and hardening findings are therefore driven by current collector posture interpretation rather than observed VM extension inventory

This produced two defensible compute interpretations:

- endpoint protection coverage remained conservatively weak in the current live profile
- workload hardening visibility remains bounded by the present compute evidence path

## Interpretation

This live result suggests a subscription posture that is not catastrophic but is clearly under-governed relative to a well-managed SME baseline.

The dominant characteristics of the observed risk profile are:

- externally reachable infrastructure
- weak network rule hygiene
- limited monitoring depth
- weak workload hardening and backup resilience
- low governance hygiene in tagging and policy coverage
- only partial tenant-wide identity visibility in the current assessment path

The result is consistent with the original CRIS-SME problem statement: SMEs and SME-like cloud environments can accumulate meaningful governance and resilience gaps even in relatively small cloud estates, while also lacking complete and affordable identity governance visibility.

## Research Value

This case study is useful academically because it contributes the live-tenant branch of the three-mode evaluation and demonstrates:

- deterministic explainable scoring on live cloud evidence
- traceable provenance from provider collection to findings
- explicit separation between observed controls and partial observability boundaries
- archived run history that supports comparison across repeated assessments
- a credible Azure-first path without overclaiming mature AI or full enterprise coverage

It also creates a practical bridge between technical implementation and dissemination:

- the HTML report can be used for demos and screenshots
- the JSON artifact can feed notebooks and figures
- the generated SVG charts can be embedded directly in markdown and slides
- archived snapshots can support longitudinal and cross-mode comparison
- the summary output can support abstracts, posters, and presentation scripts

## Current Limitations

This live assessment should be interpreted with the following boundaries:

- it is based on a single subscription rather than a comparative dataset
- Entra-wide identity controls are still only partially observable
- budget governance is still conservative rather than fully tenant-derived
- some Azure services are absent from the subscription, so not all control paths are exercised equally

These limitations do not invalidate the run. They define the current maturity boundary of the live collector.

## Next Research Steps

The most defensible next steps after this case study are:

- deepen Entra-backed IAM evidence beyond subscription role assignments
- add repeated-run comparisons so score movement can be studied over time
- compare synthetic and live scoring behavior systematically
- extend figure generation with trend and domain-comparison visuals for papers and presentations
- accumulate repeated Azure runs so the history charts move from illustrative to longitudinal

## Related Artifacts

- [cris_sme_report.json](../outputs/reports/cris_sme_report.json)
- [cris_sme_report.html](../outputs/reports/cris_sme_report.html)
- [cris_sme_summary.txt](../outputs/reports/cris_sme_summary.txt)
- [outputs/reports/history](../outputs/reports/history)
- [live_category_scores.svg](../outputs/figures/live_category_scores.svg)
- [live_priority_distribution.svg](../outputs/figures/live_priority_distribution.svg)
- [risk_trend.svg](../outputs/figures/risk_trend.svg)
- [run_comparison.svg](../outputs/figures/run_comparison.svg)
