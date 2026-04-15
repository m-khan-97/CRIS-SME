# Live Azure Case Study

This document captures a real CRIS-SME assessment run against an authenticated Azure subscription. Its purpose is to show how the framework behaves when applied to live cloud evidence rather than synthetic SME profiles alone.

## Purpose

This case study supports three goals:

- demonstrate that CRIS-SME now operates beyond mock data alone
- show how deterministic scoring and control evaluation behave on a real tenant
- provide reusable research-facing outputs for demos, posters, abstracts, and future papers

The case study should be read as an engineering validation artifact, not as a generalized benchmark of Azure SME risk.

## Assessment Context

Assessment date:
- April 14-15, 2026

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

The live report recorded the following evidence counts:

- `2` privileged assignments
- `1` privileged principal
- `0` visible Entra directory roles for the signed-in assessment identity in the current run
- `0` privileged service principal assignments
- `3` virtual machines
- `0` storage accounts
- `2` SQL servers
- `1` SQL database counted for the current data evidence path
- `0` activity log alerts
- `2` Logic Apps workflows
- `2` policy assignments
- `2` Linux VMs with password authentication enabled
- `0` VM backup-protected assets

These values were exported into the report provenance section so downstream readers can distinguish what was directly observed from what remains conservative by design.

## Headline Results

The live Azure run produced:

- overall risk score: `33.12/100`
- non-compliant findings: `16`
- evaluated profiles: `1`

Category scores:

- IAM: `14.64`
- Network: `47.41`
- Data: `39.53`
- Monitoring/Logging: `36.47`
- Compute/Workloads: `39.06`
- Cost/Governance Hygiene: `26.90`

## Figure Snapshot

![Live category scores](../outputs/figures/live_category_scores.svg)

![Live priority distribution](../outputs/figures/live_priority_distribution.svg)

![Overall risk trend](../outputs/figures/risk_trend.svg)

![Run comparison](../outputs/figures/run_comparison.svg)

The figures were generated from the current JSON report via [04-live-report-figures.ipynb](/home/muhammad-ibrahim/Github/CRIS-SME/notebooks/04-live-report-figures.ipynb) and the reusable chart exporter in [figure_export.py](/home/muhammad-ibrahim/Github/CRIS-SME/src/cris_sme/reporting/figure_export.py).

The history figures are based on archived report snapshots in [outputs/reports/history](/home/muhammad-ibrahim/Github/CRIS-SME/outputs/reports/history), which currently include a mock baseline run and a live Azure run.

## Most Significant Findings

The highest-priority observations in the current live run were:

1. `NET-001` Administrative services exposed to the public internet
2. `NET-002` Overly broad network security group rules
3. `CMP-005` Linux workloads allow password-based authentication over SSH
4. `DATA-004` Key management protections are incomplete for sensitive secrets
5. `CMP-002` Endpoint protection coverage is below the expected workload baseline

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

- all `3` VMs returned no recognized security or monitoring extensions
- no Recovery Services vaults were present for VM backup coverage
- one VM explicitly disabled password authentication
- two Linux VMs still allowed password-based authentication

This produced three defensible compute interpretations:

- endpoint protection coverage remained effectively absent
- workload backup coverage remained absent
- hardening was incomplete, but not zero, because one VM showed a stronger SSH posture

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

This case study is useful academically because it demonstrates:

- deterministic explainable scoring on live cloud evidence
- traceable provenance from provider collection to findings
- explicit separation between observed controls and partial observability boundaries
- archived run history that supports comparison across repeated assessments
- a credible Azure-first path without overclaiming mature AI or full enterprise coverage

It also creates a practical bridge between technical implementation and dissemination:

- the HTML report can be used for demos and screenshots
- the JSON artifact can feed notebooks and figures
- the generated SVG charts can be embedded directly in markdown and slides
- archived snapshots can support longitudinal or mock-versus-live comparison
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

- [cris_sme_report.json](/home/muhammad-ibrahim/Github/CRIS-SME/outputs/reports/cris_sme_report.json)
- [cris_sme_report.html](/home/muhammad-ibrahim/Github/CRIS-SME/outputs/reports/cris_sme_report.html)
- [cris_sme_summary.txt](/home/muhammad-ibrahim/Github/CRIS-SME/outputs/reports/cris_sme_summary.txt)
- [outputs/reports/history](/home/muhammad-ibrahim/Github/CRIS-SME/outputs/reports/history)
- [live_category_scores.svg](/home/muhammad-ibrahim/Github/CRIS-SME/outputs/figures/live_category_scores.svg)
- [live_priority_distribution.svg](/home/muhammad-ibrahim/Github/CRIS-SME/outputs/figures/live_priority_distribution.svg)
- [risk_trend.svg](/home/muhammad-ibrahim/Github/CRIS-SME/outputs/figures/risk_trend.svg)
- [run_comparison.svg](/home/muhammad-ibrahim/Github/CRIS-SME/outputs/figures/run_comparison.svg)
