# Evaluation Results Summary

## Evaluation Context

The current evaluation uses controlled Azure IoT Hub labs in the `uaenorth` region. The weak, simulated-clinic, and hardened-clinic runs were assessed with resource-group scoping so that each result reflects only the resources deployed for that scenario.

Healthcare IoT is reported as a standalone optional research category. The base CRIS SME overall score assigns the `IOT` category a weight of `0.0`, so the Healthcare IoT score should be interpreted separately from the standard SME risk score.

## Scenario Comparison

| Scenario | Run ID | IoMT findings | Healthcare IoT score | Key observation |
| --- | --- | ---: | ---: | --- |
| Weak IoMT baseline | `20260601004646` | `10` | `26.40` | Public IoT Hub access, no telemetry route, no IoT alert rule, overbroad shared access policies. |
| Simulated clinic | `20260601004646` | `9` | `27.08` | Diagnostics and alerting observed, but public exposure and telemetry-governance gaps remain. |
| Hardened clinic | `20260601004646` | `6` | `25.19` | Public network disabled, telemetry storage route added, IoT alerting observed, conditional private endpoint finding removed. |

## Core Controlled Result

| Scenario | `IOT-005` public exposure | `IOT-006` conditional private endpoint | `IOT-007` telemetry governance | `IOT-009` alerting | Interpretation |
| --- | --- | --- | --- | --- | --- |
| Weak baseline | Triggered | Triggered | Triggered | Triggered | CRIS-IoMT reports deliberately weak cloud-side posture. |
| Simulated clinic | Triggered | Triggered | Triggered | Not triggered | Added alerting is reflected, while exposure and routing gaps remain. |
| Hardened clinic | Not triggered | Not triggered | Not triggered | Not triggered | CRIS-IoMT reflects public exposure reduction, telemetry routing, alerting, and the conditional private endpoint rule. |

The strongest empirical claim is that deterministic IoMT controls changed in response to controlled Azure configuration differences.

## Reproducibility Command

```bash
CRIS_SME_IOMT_IOTHUB_SKU=B1 \
python3 scripts/azure_evidence_lab.py paper-iomt-suite \
  --location uaenorth \
  --yes
```

Optional stronger private endpoint experiment:

```bash
CRIS_SME_IOMT_IOTHUB_SKU=B1 \
CRIS_SME_IOMT_ENABLE_PRIVATE_ENDPOINT=true \
python3 scripts/azure_evidence_lab.py paper-iomt-suite \
  --location uaenorth \
  --yes
```

## Caveats

- The lab does not include real clinical devices or patient data.
- Defender for IoT was not observable in the Azure for Students evaluation context.
- Private endpoint evidence is optional because support may depend on subscription, SKU, and region.
- The controlled runs demonstrate cloud-governance signal separation, not production healthcare security.
