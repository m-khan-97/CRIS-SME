# Evaluation and Results Draft

This document is a draft evaluation/results section that can be reused in papers, presentations, posters, or proposal materials.

## Evaluation Scope

CRIS-SME has been evaluated across two complementary modes:

- synthetic SME posture assessment using controlled mock profiles
- live Azure-backed assessment using an authenticated subscription context

This dual-mode strategy is important because it allows the framework to support repeatable engineering tests while also demonstrating live-cloud relevance.

## Experimental Framing

The current evaluation is not framed as a benchmark against commercial CSPM tools. Instead, it is framed as a validation of three core claims:

1. CRIS-SME can turn cloud posture evidence into explainable governance findings
2. the scoring engine produces interpretable category and overall risk outputs
3. repeated-run artifacts can support comparative analysis across synthetic and live contexts

## Current Runs Available

Archived runs currently include:

- a mock assessment snapshot with an overall score of `39.90`
- multiple live Azure snapshots with an overall score of `33.12`

The latest report history comparison shows:

- history count: `5`
- delta versus previous Azure run: `0.0`
- delta versus previous distinct mock run: `-6.78`

This is useful because it separates two forms of comparison:

- stability across repeated live runs
- contrast between synthetic baseline and live Azure evidence

## Latest Live Azure Results

The latest live Azure assessment produced:

- overall risk score: `33.12/100`
- non-compliant findings: `16`
- IAM score: `14.64`
- Network score: `47.41`
- Data score: `39.53`
- Monitoring/Logging score: `36.47`
- Compute/Workloads score: `39.06`
- Cost/Governance Hygiene score: `26.90`

The most significant live findings remain concentrated in:

- public administrative service exposure
- permissive network rule posture
- workload hardening gaps
- incomplete endpoint and backup coverage
- data/key-management weaknesses

## Identity and Entra Interpretation

The identity layer is now stronger than the earlier MVP, but still intentionally conservative.

Observed identity context in the latest live run:

- `2` privileged assignments
- `1` privileged principal
- `0` visible Entra directory roles for the signed-in assessment identity
- `57` visible tenant directory-role catalog entries
- identity observability state: `broad`

This means CRIS-SME can now report richer Entra-aware context than before, while still explicitly avoiding unsupported claims about tenant-wide conditional-access enforcement.

## Per-Control Comparison

The archived-run comparison now includes control-level deltas versus the most recent distinct-mode baseline. Some of the strongest differences between the live Azure run and the mock baseline are:

- `NET-002`: `+16.68`
- `CMP-005`: `+15.46`
- `DATA-004`: `+14.83`
- `CMP-002`: `+14.83`
- `MON-002`: `+14.37`

These shifts suggest that the live environment surfaces stronger externally exposed and workload-level issues than the synthetic baseline did in those areas.

One notable negative delta is:

- `MON-001`: `-7.82`

This is useful because it shows the comparison layer can highlight not only stronger live risks, but also areas where the live environment is less severe than the mock baseline.

## Research Interpretation

The current evaluation supports several research-relevant conclusions:

- deterministic explainability remains intact even as the collector becomes more sophisticated
- provenance-aware reporting makes it easier to distinguish observed evidence from partial observability
- archived history provides a defensible base for repeated-run analysis
- mock-versus-live comparison is now concrete rather than purely conceptual

## Limitations of Current Evaluation

The present evaluation still has several boundaries:

- one live Azure subscription is not a broad empirical dataset
- repeated live runs currently show stability rather than longitudinal operational change
- Entra-wide policy visibility remains incomplete
- AWS and GCP are still at planning/scaffolding stage rather than implemented collectors

## Recommended Use in a Paper

This draft can serve as the backbone for a results section in a conference paper:

- use the archived mock run as the baseline
- use the live Azure run as the primary case study
- embed the SVG or PNG figures from `outputs/figures/`
- cite the appendix tables from `outputs/reports/results_appendix.md`
- use the control delta section to discuss why live evidence changes risk interpretation
