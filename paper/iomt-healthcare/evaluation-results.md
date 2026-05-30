# CRIS-IoMT Evaluation Results

## Evaluation Context

The first CRIS-IoMT evaluation uses controlled Azure IoT Hub labs in the `uaenorth` region. The weak, simulated-clinic, and hardened-clinic runs were assessed with a resource-group scope so that each result reflects only the resources deployed for that scenario.

Healthcare IoT is reported as a standalone optional research category. The base CRIS SME overall score currently assigns the `IOT` category a weight of `0.0`, so the Healthcare IoT score should be interpreted separately from the standard SME risk score.

## Scenario Comparison

| Metric | Clean standing demo | Weak IoMT baseline | Simulated clinic | Hardened clinic |
| --- | ---: | ---: | ---: | ---: |
| Run ID | `20260518231014` | `20260519070105` | `20260519105038` | `20260530110548` |
| Region | `uaenorth` | `uaenorth` | `uaenorth` | `uaenorth` |
| Resource-group scoped | No | Yes | Yes | Yes |
| Temporary resources deleted | No, retained for demo | Yes | Yes | Yes |
| Overall CRIS risk score | `27.20` | `33.06` | `32.16` | `32.16` |
| Healthcare IoT category score | `26.64` | `26.64` | `27.32` | `24.92` |
| Total non-compliant findings | `24` | `26` | `25` | `23` |
| `IOT-*` findings | `10` | `10` | `9` | `7` |
| IoT Hubs observed | `1` | `1` | `1` | `1` |
| Device identities observed | `1` | `1` | `3` | `0` |
| Shared access policies | `5` | `6` | `5` | `5` |
| Overbroad shared access policies | `1` | `2` | `1` | `1` |
| Diagnostic destinations | `1` | `0` | `1` | `1` |
| Diagnostic category coverage | `0.6667` | `0.0000` | `0.6667` | `0.6667` |
| Defender for IoT observed | `False` | `False` | `False` | `False` |
| Public network IoT Hubs | `1` | `1` | `1` | `0` |
| Private endpoints | `0` | `0` | `0` | `0` |
| IoT message routes | `0` | `0` | `0` | `1` |
| Telemetry storage governed | `False` | `False` | `False` | `True` |
| IoT alert rules | `0` | `0` | `1` | `1` |

## Core Controlled Results

| Scenario | `IOT-005` public exposure fires? | `IOT-007` telemetry governance fires? | `IOT-009` alerting fires? | Observed cloud evidence | Interpretation |
| --- | --- | --- | --- | --- | --- |
| Weak IoMT baseline | Yes | Yes | Yes | Public network enabled, no route, no alert rule | CRIS-IoMT reports the deliberately weak cloud-side posture. |
| Simulated clinic | Yes | Yes | No | Public network enabled, no route, one alert rule | CRIS-IoMT reflects the added alerting evidence but still reports exposure and telemetry-governance gaps. |
| Hardened clinic | No | No | No | Public network disabled, one storage route, one alert rule | CRIS-IoMT distinguishes the hardened scenario across three deterministic cloud-side controls. |

This is the strongest empirical result in the current study. The scenario set now differs by concrete Azure control-plane artefacts, and the deterministic control outcomes change accordingly. The result should still be framed as controlled-lab feasibility evidence, not as proof of production healthcare security.

## Triggered IoMT Controls

| Control | Weak IoMT baseline | Simulated clinic | Hardened clinic | Interpretation |
| --- | --- | --- | --- | --- |
| `IOT-001` Device identity authentication evidence | Triggered | Triggered | Triggered | The hardened clinic disabled public network access before assessment, which made device identity inventory unavailable to the lab runner; this is treated as an observability caveat rather than a device-security failure. |
| `IOT-002` Shared access policy least privilege | Triggered | Triggered | Triggered | All scenarios retain default or broad IoT Hub shared-access policy exposure. |
| `IOT-003` Diagnostic logging | Triggered | Triggered | Triggered | Diagnostics exist in the simulated and hardened runs, but Azure reports category coverage below the current 80% baseline. |
| `IOT-004` Defender/security monitoring | Triggered | Triggered | Triggered | Defender for IoT or equivalent security monitoring was not observed. In this Azure for Students evaluation, this is a monitoring-evidence/observability gap rather than proof that no compensating monitoring could exist. |
| `IOT-005` Public network access | Triggered | Triggered | Not triggered | The hardened clinic disabled public network access after configuration. |
| `IOT-006` Private endpoint coverage | Triggered | Triggered | Triggered | No private endpoint coverage was observed for sensitive IoMT telemetry paths. |
| `IOT-007` Telemetry routing and retention | Triggered | Triggered | Not triggered | The hardened clinic added a storage routing endpoint and message route. |
| `IOT-008` Secret governance | Triggered | Triggered | Triggered | IoT credential governance was not linked to managed secret rotation evidence. |
| `IOT-009` Clinical alert routing | Triggered | Not triggered | Not triggered | The simulated and hardened clinic scenarios added IoT metric alerts; the weak baseline did not. |
| `IOT-010` Clinical-operational ownership boundary | Triggered | Triggered | Triggered | Human validation is still required for clinical-operational responsibility boundaries. |

## Result Summary

The controlled runs support the central CRIS-IoMT claim: cloud control-plane telemetry can expose meaningful healthcare IoT governance weaknesses without inspecting patient data, clinical telemetry payloads, device firmware, or radio/sensing layers.

The weak baseline, simulated clinic, and hardened clinic all produced deterministic IoMT findings. The simulated clinic removed the operational-alerting finding after adding an IoT-specific alert rule. The hardened clinic removed three cloud-side findings after adding alerting, adding telemetry routing, and disabling public IoT Hub network access. This is a useful early signal that CRIS-IoMT can reflect controlled cloud-side configuration differences across multiple IoMT governance controls.

The results should not be reported as evidence of full healthcare IoT security. They are evidence of cloud-side governance posture only.
