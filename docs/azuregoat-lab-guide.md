# AzureGoat Lab Guide

## Purpose

This guide explains how to use AzureGoat as a lawful, intentionally vulnerable Azure dataset track for CRIS-SME research and evaluation.

AzureGoat is a deliberately vulnerable Azure environment published by INE. It is deployed into your own Azure account using Terraform and is therefore suitable for:

- control stress testing
- richer Azure case-study evaluation
- dataset expansion beyond the current synthetic baseline and single live tenant

Reference source:

- AzureGoat repository: https://github.com/ine-labs/AzureGoat

## Why AzureGoat Matters for CRIS-SME

CRIS-SME already has:

- synthetic SME baseline data
- an authorized live Azure case-study environment

AzureGoat adds a third valuable dataset type:

- intentionally vulnerable Azure infrastructure with known misconfigurations

That makes it useful for:

- testing whether CRIS-SME surfaces high-variance controls clearly
- evaluating budget-aware remediation under more severe posture conditions
- producing a second Azure-based case study for paper results

## Safety and Scope Rules

AzureGoat should only be used in:

- an isolated Azure subscription you control
- a clearly designated lab or research resource group
- a disposable environment used for training and assessment

Do not point CRIS-SME at unrelated public Azure infrastructure and treat it as equivalent to AzureGoat. The value of AzureGoat is that it is explicitly deployable by you and intentionally vulnerable by design.

## AzureGoat Deployment Summary

AzureGoat’s own repository describes the current high-level flow as:

1. clone the AzureGoat repository
2. authenticate to Azure CLI
3. create the required resource group
4. run `terraform init`
5. run `terraform apply --auto-approve`

Before using it for CRIS-SME research, verify the latest deployment instructions in the upstream AzureGoat README.

## CRIS-SME Assessment Workflow for AzureGoat

Once AzureGoat is deployed into your lab subscription, the cleanest CRIS-SME workflow is:

```bash
PYTHONPATH=src python3 scripts/run_azuregoat_assessment.py
```

This helper automatically tags the resulting report as:

- `dataset_source_type = vulnerable_lab`
- `authorization_basis = intentionally_vulnerable_lab`
- `dataset_use = control_stress_test`

If you want more control, you can use the generic snapshot runner instead:

```bash
python3 scripts/run_assessment_snapshot.py \
  --collector azure \
  --dataset-source-type vulnerable_lab \
  --authorization-basis intentionally_vulnerable_lab \
  --dataset-use control_stress_test
```

## Recommended Metadata

For AzureGoat runs, use:

- organization name: `AzureGoat Lab`
- sector: `Training Lab`
- source type: `vulnerable_lab`
- authorization basis: `intentionally_vulnerable_lab`
- use case: `control_stress_test`

This keeps the lab dataset clearly separated from:

- real SME case studies
- synthetic baseline runs
- sandbox-based experiments

## Suggested Research Use

AzureGoat should be used in the paper as:

- a vulnerable-lab dataset
- a control stress-test environment
- a complement to the real Azure case study, not a replacement for it

The strongest paper use is:

1. synthetic baseline for repeatability
2. authorized live Azure tenant for real-case validation
3. AzureGoat for intentionally vulnerable stress testing

That combination gives CRIS-SME:

- reproducibility
- realism
- controlled adverse-case evaluation

## Recommended Next Steps After Deployment

After you deploy AzureGoat, the next CRIS-SME tasks should be:

1. run the AzureGoat assessment and archive the snapshot
2. register the run in the evaluation dataset track
3. compare AzureGoat category scores against the synthetic and live Azure baselines
4. update `docs/paper-results-tables.md` with an AzureGoat comparison row

## Reporting Expectation

An AzureGoat run is expected to produce:

- stronger exposure-related findings
- richer network and data misconfiguration signals
- higher-value remediation opportunities for the action-plan and budget-aware layers

That makes it a very good candidate for a second paper case study.
