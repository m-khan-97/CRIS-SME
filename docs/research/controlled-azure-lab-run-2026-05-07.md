# Controlled Azure Vulnerable-Lab Run - 2026-05-07

This note records the CRIS-SME controlled Azure lab run used as a vulnerable-lab evidence track for Cyber Essentials research.

## Purpose

The lab was created to test whether CRIS-SME detects intentionally weak cloud-control-plane signals without deploying a reachable workload.

The lab is not a full AzureGoat deployment. AzureGoat remains useful for later richer application-layer testing, but this controlled lab is safer, cheaper, and more repeatable inside an Azure for Students subscription.

## Subscription Context

- Subscription: Azure for Students
- Tenant: Ulster University
- Dataset source type: `vulnerable_lab`
- Authorization basis: `intentionally_vulnerable_lab`
- Dataset use: `control_stress_test`

## Lab Architecture

Resource group attempted first:

- `cris-ce-lab-202605071824`
- Region: `uksouth`
- Result: resource group creation succeeded, but resource creation was blocked by Azure policy.

Working lab resource group:

- `cris-ce-lab-202605071830`
- Region: `germanywestcentral`

Created resources:

- Network Security Group: `cris-ce-lab-open-admin-nsg`
- Storage account: `crisce260507183001`
- Empty blob container: `public-evidence-lab`

Intentional weak signals:

- inbound SSH from `Internet` to port `22`
- inbound RDP from `Internet` to port `3389`
- storage account with public network access enabled
- blob public access enabled

No VM was deployed and no live administrative service was attached to the NSG.

## CRIS-SME Run

Command shape:

```bash
PYTHONPATH=src \
CRIS_SME_COLLECTOR=azure \
CRIS_SME_OUTPUT_DIR=outputs/reports/azure_controlled_lab \
CRIS_SME_AZURE_ORGANIZATION_NAME="CRIS Controlled Azure Lab" \
CRIS_SME_AZURE_SECTOR="Training Lab" \
CRIS_SME_DATASET_SOURCE_TYPE=vulnerable_lab \
CRIS_SME_AUTHORIZATION_BASIS=intentionally_vulnerable_lab \
CRIS_SME_DATASET_USE=control_stress_test \
python3 -m cris_sme.main
```

AI-assisted pilot CE review draft:

```bash
PYTHONPATH=src python3 scripts/build_ce_review_draft.py \
  --answer-pack outputs/reports/azure_controlled_lab/cris_sme_ce_self_assessment.json \
  --output-dir outputs/reports/azure_controlled_lab/ce_review_draft \
  --reviewer "AI-assisted controlled-lab pilot reviewer draft"
```

## Results

Overall CRIS-SME result:

- Overall risk score: `40.16/100`
- Non-compliant findings: `18`

Category scores:

| Category | Score |
| --- | ---: |
| IAM | 32.51 |
| Network | 58.42 |
| Data | 41.74 |
| Monitoring/Logging | 36.38 |
| Compute/Workloads | 38.29 |
| Cost/Governance Hygiene | 27.11 |

Top lab-sensitive findings:

| Control | Finding | Priority | Score |
| --- | --- | --- | ---: |
| NET-001 | Administrative services are exposed to the public internet | High | 72.12 |
| IAM-001 | Privileged role assignments without MFA enforcement | High | 67.97 |
| DATA-001 | Public storage access increases data exposure risk | Planned | 48.35 |
| NET-002 | Network security group rules are broader than expected | Planned | 44.71 |

Relevant evidence:

- `1 asset(s) expose RDP to the public internet`
- `1 asset(s) expose SSH to the public internet`
- `1 storage asset(s) allow public access`
- `2 permissive NSG rule(s) were identified`

Collector coverage:

- observed: `azure_role_assignments_and_graph`
- observed: `azure_network_cli_inventory`
- observed: `azure_storage_cli_inventory`
- observed: `azure_monitor_cli_inventory`
- observed: `azure_compute_inventory_no_vms`
- observed: `azure_resource_inventory`
- partially observed: `tenant_identity_controls`
- unavailable: `conditional_access_tenant_scope`

## Cyber Essentials Output

Question-level CE observability:

- total mapped entries: `106`
- technical entries: `62`
- cloud-supported entries: `28` (`26.42%`)
- technical cloud-supported entries: `22` (`35.48%`)
- direct cloud entries: `5`
- inferred cloud entries: `23`
- non-cloud evidence required: `78`

Proposed CE answers:

- `No`: `23`
- `Yes`: `5`
- `Cannot determine`: `78`

AI-assisted pilot review draft:

- reviewed draft entries: `28`
- accepted: `23`
- needs evidence: `5`
- pending: `78`
- agreement-evaluable draft entries: `23`
- draft agreement: `23/23`

This agreement number is internal pilot plumbing only. It must not be reported as independent human expert agreement unless a CE-knowledgeable reviewer validates the ledger.

## Cleanup

Both lab resource groups were deleted after the run:

- `cris-ce-lab-202605071830`
- `cris-ce-lab-202605071824`

Deletion was confirmed with `az group wait --deleted`.

## Paper Use

Recommended wording:

> We evaluated CRIS-SME on a controlled vulnerable Azure lab containing deliberately weak control-plane signals: public administrative NSG rules and an empty public-network storage account. No VM was attached to the administrative exposure rules. The run demonstrates that CRIS-SME surfaces cloud-control-plane evidence into both deterministic risk findings and Cyber Essentials question-level pre-population artifacts.

Threats to validity:

- This was a controlled lab, not a complete SME production tenant.
- The lab was intentionally small to avoid cost and avoid exposing a reachable workload.
- The AI-assisted review ledger is not independent human assessor agreement.
- Conditional Access remained unavailable in this subscription-scoped run and is represented as an explicit observability boundary.
