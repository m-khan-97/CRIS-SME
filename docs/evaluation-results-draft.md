# Evaluation and Results Draft

> Status: draft / historical narrative.  
> Values in this file are intended for manuscript drafting and may reflect frozen snapshots rather than the latest local run.

This document is a draft evaluation/results section that can be reused in papers, presentations, posters, or proposal materials.

## Evaluation Scope

CRIS-SME has been evaluated across three complementary modes:

- synthetic SME posture assessment using controlled mock profiles
- live Azure-backed assessment using an authenticated subscription context
- controlled Azure vulnerable-lab assessment using intentionally weak cloud-control-plane signals

This three-mode strategy is important because it allows the framework to support repeatable engineering tests, live-cloud case-study evidence, and intentionally stressed cloud posture without relying on unauthorized public infrastructure.

## Experimental Framing

The current evaluation is not framed as a benchmark against commercial CSPM tools. Instead, it is framed as a validation of three core claims:

1. CRIS-SME can turn cloud posture evidence into explainable governance findings
2. the scoring engine produces interpretable category and overall risk outputs
3. repeated-run artifacts can support comparative analysis across synthetic and live contexts

## Current Runs Available

Archived runs currently include:

- a mock assessment snapshot with an overall score of `39.84`
- a latest live Azure case-study snapshot with an overall score of `27.81`
- a controlled Azure vulnerable-lab snapshot with an overall score of `40.16`

The latest controlled vulnerable-lab validation run, executed on May 7, 2026, produced an overall score of `40.16/100` from live Azure evidence after CRIS-SME created a small authorized lab in `germanywestcentral`. This run is now the preferred vulnerable-lab baseline for manuscript drafting because it is documented, bounded, and was cleaned up after the assessment.

For the latest live Azure case-study snapshot:

- delta versus previous Azure run: `0.0`
- delta versus previous distinct mock run: `-7.05`

This is useful because it separates two forms of comparison:

- stability across repeated live runs
- contrast between synthetic baseline and live Azure evidence

It also creates a third evaluation lens:

- stress testing against an intentionally vulnerable Azure lab in an explicitly authorized environment

Taken together, these runs should now be presented as a three-mode evaluation rather than as one primary case study plus supporting runs.

## Three-Mode Headline Results

The current three-mode comparison is:

- synthetic SME baseline: `39.84/100`, `50` generated findings, `49` non-compliant findings
- latest live Azure case-study snapshot: `27.81/100`, `15` generated findings, `15` non-compliant findings
- controlled Azure vulnerable-lab snapshot: `40.16/100`, `18` generated findings, `18` non-compliant findings

This framing is stronger than a single-primary narrative because it shows that CRIS-SME has been exercised across controlled synthetic evidence, authorized live cloud evidence, and an intentionally stressed but lawful lab environment.

## Live Azure Results

The latest live Azure assessment produced:

- overall risk score: `27.81/100`
- non-compliant findings: `15`
- IAM score: `32.51`
- Network score: `0.00`
- Data score: `38.44`
- Monitoring/Logging score: `36.38`
- Compute/Workloads score: `38.29`
- Cost/Governance Hygiene score: `27.11`

The most significant live findings remain concentrated in:

- endpoint protection and workload hardening gaps
- data/key-management weaknesses
- tenant identity observability boundaries
- monitoring and governance coverage gaps

The clean live Azure run contained no detected network exposure, which is useful because it provides contrast with the controlled vulnerable-lab track.

## Controlled Azure Vulnerable-Lab Results

The current controlled Azure vulnerable-lab assessment produced:

- overall risk score: `40.16/100`
- non-compliant findings: `18`
- dataset source type: `vulnerable_lab`
- authorization basis: `intentionally_vulnerable_lab`
- dataset use: `control_stress_test`

The controlled lab is important for the evaluation because it introduces a high-variance but ethically defensible test environment. CRIS-SME observed substantial risk across:

- network exposure and permissive security-group posture
- public or weakly governed data paths
- monitoring and workload hardening gaps
- governance weakness in an intentionally exposed cloud-control-plane environment

One important methodological note is that this was a controlled lab, not a fully stock AzureGoat rollout. It used public SSH/RDP NSG rules and an empty public-network storage account; no VM was attached to the public administrative rules.

## Identity and Entra Interpretation

The identity layer is now stronger than the earlier MVP, but still intentionally conservative.

Observed identity context in the latest live Azure case-study snapshot:

- `2` privileged assignments
- `1` privileged principal
- `0` visible Entra directory roles for the signed-in assessment identity
- `57` visible tenant directory-role catalog entries
- identity observability state: `broad`

This means CRIS-SME can now report richer Entra-aware context than before, while still explicitly avoiding unsupported claims about tenant-wide conditional-access enforcement.

## Per-Control Comparison

The archived-run comparison now includes control-level deltas versus the most recent distinct-mode baseline. Some of the strongest differences between the live Azure run and the mock baseline are:

- `CMP-002`: `+14.83`
- `DATA-004`: `+14.73`
- `MON-002`: `+14.37`
- `DATA-003`: `+14.09`
- `CMP-004`: `+13.82`

These shifts suggest that the live environment surfaces stronger externally exposed and workload-level issues than the synthetic baseline did in those areas.

One notable negative delta is:

- `DATA-001`: `-10.14`

This is useful because it shows the comparison layer can highlight not only stronger live risks, but also areas where the live environment is less severe than the mock baseline.

## Research Interpretation

The current evaluation supports several research-relevant conclusions:

- deterministic explainability remains intact even as the collector becomes more sophisticated
- provenance-aware reporting makes it easier to distinguish observed evidence from partial observability
- archived history provides a defensible base for repeated-run analysis
- mock-versus-live comparison is now concrete rather than purely conceptual
- intentionally vulnerable lab evidence provides a lawful, higher-variance third mode for evaluation

## Limitations of Current Evaluation

The present evaluation still has several boundaries:

- one live Azure subscription is not a broad empirical dataset
- one vulnerable-lab deployment is not the same as a broad benchmark corpus
- repeated live runs currently show stability rather than longitudinal operational change
- Entra-wide policy visibility remains incomplete
- AWS and GCP are still at planning/scaffolding stage rather than implemented collectors

## Recommended Use in a Paper

This draft can serve as the backbone for a results section in a conference paper:

- present the three modes together in a single headline table
- treat synthetic, live Azure, and controlled vulnerable lab as equal first-class evidence classes
- use the live Azure subsection for real-tenant feasibility and native-tool comparison
- use the controlled-lab subsection for lawful stress behavior and control-path coverage
- embed the SVG or PNG figures from `outputs/figures/`
- cite the appendix tables from `outputs/reports/results_appendix.md`
- use the control delta section to discuss why live evidence changes risk interpretation
- disclose the controlled-lab design and absence of a reachable workload in the threats-to-validity discussion
