# Evaluation Dataset Track

## Purpose

This document defines how CRIS-SME should build a research dataset safely and credibly.

The core principle is simple:

CRIS-SME should not be evaluated by probing arbitrary public cloud infrastructure.

Instead, the dataset should be built from environments that are:

- synthetic and fully controlled
- owned by the researcher
- explicitly authorized for assessment
- provided as provider sandboxes
- intentionally vulnerable training labs

This is both an ethics requirement and a research-quality requirement.

## Why Public Infrastructure Is Not the Right Dataset

CRIS-SME is not only an external scanner. Many of its strongest controls depend on authenticated cloud context such as:

- IAM and privileged role posture
- policy assignments
- budget alerts
- backup coverage
- monitoring posture
- encryption settings
- private endpoint coverage

Random internet-facing infrastructure does not provide enough authenticated context for a meaningful governance dataset. Even if public exposure can be observed, most of the framework’s research value comes from the combination of:

- control evidence
- explainable scoring
- compliance mapping
- budget-aware remediation
- provenance and observability boundaries

That means the most useful evaluation dataset is not “whatever is public.” It is “what is lawful, authorized, and structurally rich enough to support governance assessment.”

## Approved Dataset Classes

CRIS-SME should organize evaluation data into four classes.

### 1. Synthetic

Examples:

- `data/synthetic_sme_profiles.json`

Use:

- repeatable baseline experiments
- regression testing
- controlled scenario design

Authorization basis:

- `synthetic_dataset`

### 2. Live Real

Examples:

- owned Azure tenant
- explicitly authorized partner or lab tenant

Use:

- main case studies
- live validation
- native-tool comparison

Authorization basis:

- `authorized_tenant_access`

### 3. Sandbox

Examples:

- Microsoft Learn sandbox
- Azure Sandbox architecture/project

Use:

- reproducible platform exercises
- low-risk experimentation
- additional benchmark candidates

Authorization basis:

- `provider_sandbox`

### 4. Vulnerable Lab

Examples:

- AzureGoat
- future AWS lab tracks such as CloudGoat

Use:

- control stress testing
- richer case studies
- intentionally misconfigured environment analysis

Authorization basis:

- `intentionally_vulnerable_lab`

## Metadata Requirements

Every dataset or environment used in CRIS-SME evaluation should carry the following metadata:

- `source_type`
- `authorization_basis`
- `use_case`
- `provider`
- `status`
- `environment_scope`
- `ethics_note`

These fields are now represented in:

- `data/evaluation_dataset_schema.json`
- `data/evaluation_dataset_catalog.json`

And report-level summaries now expose:

- `evaluation_dataset.source_types`
- `evaluation_dataset.authorization_bases`
- `evaluation_dataset.dataset_uses`

## Initial Dataset Roadmap

The best research dataset sequence for CRIS-SME is:

1. keep the synthetic baseline as the reproducible control set
2. keep the current authorized live Azure track as the real-cloud evidence branch
3. maintain the Azure Evidence Lab as the repeatable controlled live-lab branch
4. add a Microsoft sandbox track for safe reproducible platform experiments
5. maintain an AzureGoat track for intentionally vulnerable Azure scenarios as a broader stress-test branch
6. later add additional consented or owned real environments for comparative analysis

This sequence gives CRIS-SME:

- repeatability
- realism
- safety
- publishable evaluation structure

## Recommended Next Dataset Expansions

The current controlled-lab workflow is implemented in [Azure Evidence Lab](azure-evidence-lab.md). The next strongest dataset-building tasks are:

1. run the Azure Evidence Lab scenarios across several days and archive the output manifests
2. create a small ingestion format for adding new evaluation runs into the dataset catalog
3. run CRIS-SME against an Azure sandbox environment where terms allow
4. deploy AzureGoat in an isolated subscription and capture a dedicated assessment snapshot
5. update `docs/paper-results-tables.md` and the three-mode comparison once those runs exist

## Research and Ethics Positioning

For the paper, the evaluation section should state clearly:

- CRIS-SME was evaluated on synthetic profiles, owned or explicitly authorized live environments, and approved sandbox/lab environments
- arbitrary public cloud infrastructure was not used as an assessment dataset
- this restriction is intentional because the framework emphasizes authenticated governance posture, ethical scope control, and reproducible research design

That is a stronger and more defensible paper position than claiming “public internet scale” coverage with incomplete governance visibility.
