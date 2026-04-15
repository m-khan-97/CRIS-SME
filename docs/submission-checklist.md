# Submission Checklist

This checklist is intended to help move CRIS-SME from a strong research repo into a submission-ready conference package.

## Paper Core

- finalize [manuscript-draft.md](/home/muhammad-ibrahim/Github/CRIS-SME/docs/manuscript-draft.md)
- refine [conference-abstract-draft.md](/home/muhammad-ibrahim/Github/CRIS-SME/docs/conference-abstract-draft.md) to match the target venue word limit
- align terminology across architecture, methodology, scoring, and evaluation sections
- ensure all numeric results match the latest archived live assessment

## Figures and Tables

- confirm latest SVG and PNG figures in [outputs/figures](/home/muhammad-ibrahim/Github/CRIS-SME/outputs/figures)
- select 2-4 figures for the paper body
- select appendix tables from [results_appendix.md](/home/muhammad-ibrahim/Github/CRIS-SME/outputs/reports/results_appendix.md)
- confirm `prioritized_risks.csv` is suitable for external plotting or spreadsheet cleanup if needed

## Evaluation Readiness

- verify the latest archived live run under [outputs/reports/history](/home/muhammad-ibrahim/Github/CRIS-SME/outputs/reports/history)
- document whether the live Azure result is stable across repeated runs
- decide whether to present mock-versus-live comparison as a baseline experiment or supplementary analysis
- explicitly state IAM and Entra observability limits

## Repository and Reproducibility

- confirm `python3 -m pytest` passes
- confirm `python scripts/run_assessment_snapshot.py --collector mock` works cleanly
- confirm the live Azure path still runs in the authenticated environment
- verify README documentation matches the current repo capabilities

## Venue Preparation

- identify the target venue and word/page limits
- adapt the manuscript into the venue template
- reduce or expand the evaluation/results section based on space
- tailor the contribution framing to the venue audience

## Final Packaging

- export final figures at publication-ready resolution
- freeze the specific archived run(s) used in the paper
- create a paper-specific branch or release tag if needed
- add a concise “artifact package” note to the repo if the submission requires it
