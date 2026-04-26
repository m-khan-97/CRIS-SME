# Evaluation and Results Draft

> Status: draft / historical narrative.  
> Values in this file are intended for manuscript drafting and may reflect frozen snapshots rather than the latest local run.

This document is a draft evaluation/results section that can be reused in papers, presentations, posters, or proposal materials.

## Evaluation Scope

CRIS-SME has been evaluated across three complementary modes:

- synthetic SME posture assessment using controlled mock profiles
- live Azure-backed assessment using an authenticated subscription context
- AzureGoat-derived vulnerable-lab assessment using an intentionally vulnerable Azure environment

This three-mode strategy is important because it allows the framework to support repeatable engineering tests, live-cloud case-study evidence, and intentionally stressed cloud posture without relying on unauthorized public infrastructure.

## Experimental Framing

The current evaluation is not framed as a benchmark against commercial CSPM tools. Instead, it is framed as a validation of three core claims:

1. CRIS-SME can turn cloud posture evidence into explainable governance findings
2. the scoring engine produces interpretable category and overall risk outputs
3. repeated-run artifacts can support comparative analysis across synthetic and live contexts

## Current Runs Available

Archived runs currently include:

- a mock assessment snapshot with an overall score of `39.84`
- a latest live Azure case-study snapshot with an overall score of `32.79`
- an AzureGoat vulnerable-lab snapshot with an overall score of `32.79`

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
- latest live Azure case-study snapshot: `32.79/100`, `19` generated findings, `18` non-compliant findings
- AzureGoat-derived vulnerable-lab snapshot: `32.79/100`, `18` generated findings, `18` non-compliant findings

This framing is stronger than a single-primary narrative because it shows that CRIS-SME has been exercised across controlled synthetic evidence, authorized live cloud evidence, and an intentionally stressed but lawful lab environment.

## Live Azure Results

The latest live Azure assessment produced:

- overall risk score: `32.79/100`
- non-compliant findings: `18`
- IAM score: `14.78`
- Network score: `38.02`
- Data score: `48.65`
- Monitoring/Logging score: `36.38`
- Compute/Workloads score: `38.29`
- Cost/Governance Hygiene score: `24.80`

The most significant live findings remain concentrated in:

- public storage exposure
- public administrative service exposure
- endpoint protection and workload hardening gaps
- data/key-management weaknesses

## AzureGoat Vulnerable-Lab Results

The current AzureGoat-derived vulnerable-lab assessment produced:

- overall risk score: `32.79/100`
- non-compliant findings: `18`
- dataset source type: `vulnerable_lab`
- authorization basis: `intentionally_vulnerable_lab`
- dataset use: `control_stress_test`

The AzureGoat run is important for the evaluation because it introduces a high-variance but ethically defensible test environment. In the current constrained deployment variant, CRIS-SME still observed substantial risk across:

- network exposure and permissive security-group posture
- public or weakly governed data paths
- monitoring and workload hardening gaps
- governance weakness in an intentionally exposed application environment

One important methodological note is that this was not a fully stock AzureGoat rollout. The deployment had to be adapted for subscription-policy constraints, including region restrictions, blocked Automation Account deployment, Basic public-IP restrictions, and repeated VM-capacity failures. Those constraints should be disclosed in the paper, but they do not invalidate the dataset class.

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
- treat synthetic, live Azure, and AzureGoat as equal first-class evidence classes
- use the live Azure subsection for real-tenant feasibility and native-tool comparison
- use the AzureGoat subsection for lawful stress behavior and control-path coverage
- embed the SVG or PNG figures from `outputs/figures/`
- cite the appendix tables from `outputs/reports/results_appendix.md`
- use the control delta section to discuss why live evidence changes risk interpretation
- disclose the constrained AzureGoat deployment adaptation in the threats-to-validity discussion
