# Azure Evidence Lab

The Azure Evidence Lab is a repeatable way to create small, controlled Azure architectures, run CRIS-SME against live Azure control-plane evidence, archive the outputs, and then delete the lab resources.

The goal is to replace over-reliance on mock profiles with lawful, labelled, reproducible live evidence.

## Why This Exists

CRIS-SME needs three evidence tracks:

- synthetic profiles for deterministic regression testing
- owned or explicitly authorised live subscriptions for realism
- intentionally vulnerable labs for stress-testing control decisions

The Azure Evidence Lab is the third track, with a clean-baseline option for contrast. It is not a random internet scanner and it does not assess third-party infrastructure.

## Scenarios

Scenario definitions live in:

`labs/azure-evidence-lab/scenarios.json`

Current scenarios:

- `clean-baseline`: conservative storage and network defaults
- `public-exposure`: public SSH/RDP NSG rules and public blob access
- `governance-drift`: intentionally incomplete tagging and governance posture
- `data-risk`: public blob access plus weak key-management evidence
- `media-office-demo`: public-communications style training estate with web-only exposure, public media content storage, and protected key vault
- `media-office-delegated`: richer media-office training estate with delegated edge, editorial, data, and monitoring zones

Each scenario declares:

- dataset source type
- authorisation basis
- dataset use
- risk intent
- expected finding behaviour
- resource types deployed

## Daily Dataset Workflow

First confirm Azure CLI is authenticated to the intended subscription:

```bash
az account show
```

List available scenarios:

```bash
python3 scripts/azure_evidence_lab.py list
```

Preview a scenario without creating resources:

```bash
python3 scripts/azure_evidence_lab.py deploy \
  --scenario public-exposure \
  --location uksouth \
  --run-id paper-day-001 \
  --dry-run
```

Run a complete deploy, assess, and cleanup cycle:

```bash
python3 scripts/azure_evidence_lab.py cycle \
  --scenario public-exposure \
  --location uksouth \
  --run-id paper-day-001
```

Keep the lab after assessment for manual inspection:

```bash
python3 scripts/azure_evidence_lab.py cycle \
  --scenario data-risk \
  --location uksouth \
  --run-id paper-day-002 \
  --keep
```

Clean up a kept lab:

```bash
python3 scripts/azure_evidence_lab.py cleanup \
  --scenario data-risk \
  --run-id paper-day-002
```

## Output Location

Assessment outputs are archived under:

`outputs/evidence-lab/{run_id}/{scenario}/reports/`

Each run includes:

- normal CRIS-SME report artifacts
- `lab_manifest.json`
- scenario metadata
- expected-finding notes
- dataset labels embedded in the CRIS-SME report

These outputs can be used directly in the paper dataset table, evaluation appendix, and frontend demo artifacts.

## Safety Model

The lab harness is deliberately resource-group scoped.

It creates resource groups named:

`cris-lab-{scenario}-{run_id}`

It tags managed lab resources with:

- `cris-sme-lab=true`
- `cris-sme-scenario`
- `cris-sme-run-id`
- `cris-sme-purpose=evidence-dataset`

Cleanup deletes the selected lab resource group only. Do not point the cleanup command at non-lab resource groups.

## Research Framing

Recommended wording:

> We evaluated CRIS-SME on controlled Azure evidence-lab scenarios deployed into an authorised subscription. These scenarios introduced known cloud-control-plane states, including public administrative ingress, public blob exposure, governance drift, and clean baseline resources. The lab outputs were labelled as controlled live-lab evidence rather than production SME evidence.

Important limitation:

> The lab scenarios provide controlled ground truth for specific Azure control-plane signals. They do not represent full enterprise workloads, endpoint fleets, or arbitrary real-world SME diversity.

## Next Extensions

The strongest next additions are:

- before/after remediation scenario pairs
- diagnostic-settings and logging scenario
- private endpoint scenario
- budget-alert scenario
- Intune or Defender for Endpoint enrichment track for Cyber Essentials endpoint questions
