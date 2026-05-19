# CRIS-IoMT Live Run Register

This register records live Azure IoMT evidence runs used for the CRIS-IoMT research track. The goal is reproducibility and traceability: each row links a controlled scenario to its generated CRIS report and IoMT evidence pack.

## Azure Policy Context

- Subscription: Azure for Students, `609d2aab-0611-4bbf-a5ff-127c2e74bf4c`
- Tenant: Ulster University, `6f0b9487-4fa8-42a8-aeb4-bf2e2c22d4e8`
- Policy assignment: `Allowed resource deployment regions`
- Allowed regions: `uaenorth`, `polandcentral`, `switzerlandnorth`, `spaincentral`, `germanywestcentral`
- IoT Hub-compatible allowed regions observed: `uaenorth`, `switzerlandnorth`, `germanywestcentral`
- Selected evaluation region: `uaenorth`

## Run Register

| Run ID | Scenario | Region | Resource group scope | Cleanup status | Report | IoMT evidence pack | Headline result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `20260518231014` | Clean standing demo baseline | `uaenorth` | `cris-lab-iomt-clean-baseline-20260518231014` | retained for demos | `outputs/iomt-validation/live-20260519-fresh/cris_sme_report.json` | `outputs/iomt-validation/live-20260519-fresh/cris_iomt_evidence_pack.md` | Live collector validated IoT Hub evidence path; 10 `IOT-*` findings, Healthcare IoT score `26.64`. |
| `20260519070105` | Weak IoMT baseline | `uaenorth` | `cris-lab-iomt-weak-baseline-20260519070105` | deleted by cycle command | `outputs/evidence-lab/20260519070105/iomt-weak-baseline/reports/cris_sme_report.json` | `outputs/evidence-lab/20260519070105/iomt-weak-baseline/reports/cris_iomt_evidence_pack.md` | Scenario-scoped weak posture: 1 IoT Hub, 1 device identity, 6 shared access policies, 2 overbroad policies, no diagnostics, no alert rule; 10 `IOT-*` findings. |
| `20260519105038` | Simulated clinic | `uaenorth` | `cris-lab-iomt-simulated-clinic-20260519105038` | deleted by cycle command | `outputs/evidence-lab/20260519105038/iomt-simulated-clinic/reports/cris_sme_report.json` | `outputs/evidence-lab/20260519105038/iomt-simulated-clinic/reports/cris_iomt_evidence_pack.md` | Scenario-scoped simulated clinic: 1 IoT Hub, 3 device identities, diagnostics enabled, 1 alert rule, 1 overbroad policy; 9 `IOT-*` findings. |

## Methodological Notes

- The weak and simulated-clinic runs used resource-group-scoped assessment via `CRIS_SME_AZURE_RESOURCE_GROUP_SCOPE` to prevent the standing demo IoT Hub from contaminating scenario counts.
- Temporary lab resources were created, assessed, and deleted by `scripts/azure_evidence_lab.py cycle`.
- The clean standing demo resource group is intentionally retained for browser demos and should not be treated as an isolated paper experiment unless scanned with resource-group scope.
- The IoMT evidence packs are generated artifacts and are intentionally not committed to the repository because they may contain live environment identifiers. The paper should report aggregate counts and control outcomes rather than raw resource identifiers.

## Reproduction Commands

```bash
CRIS_SME_IOMT_IOTHUB_SKU=B1 \
python3 scripts/azure_evidence_lab.py cycle \
  --scenario iomt-weak-baseline \
  --location uaenorth \
  --yes
```

```bash
CRIS_SME_IOMT_IOTHUB_SKU=B1 \
python3 scripts/azure_evidence_lab.py cycle \
  --scenario iomt-simulated-clinic \
  --location uaenorth \
  --yes
```

```bash
PYTHONPATH=src python3 scripts/build_iomt_evidence_pack.py \
  --report outputs/evidence-lab/<run-id>/<scenario>/reports/cris_sme_report.json \
  --manifest outputs/evidence-lab/<run-id>/<scenario>/lab_manifest.json
```
