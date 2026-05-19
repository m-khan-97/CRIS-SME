# CRIS-IoMT Evaluation Results

## Evaluation Context

The first CRIS-IoMT evaluation uses controlled Azure IoT Hub labs in the `uaenorth` region. The weak and simulated-clinic runs were assessed with a resource-group scope so that each result reflects only the resources deployed for that scenario.

## Scenario Comparison

| Metric | Clean standing demo | Weak IoMT baseline | Simulated clinic |
| --- | ---: | ---: | ---: |
| Run ID | `20260518231014` | `20260519070105` | `20260519105038` |
| Region | `uaenorth` | `uaenorth` | `uaenorth` |
| Resource-group scoped | No | Yes | Yes |
| Temporary resources deleted | No, retained for demo | Yes | Yes |
| Overall CRIS risk score | `27.20` | `33.06` | `32.16` |
| Healthcare IoT category score | `26.64` | `26.64` | `27.32` |
| Total non-compliant findings | `24` | `26` | `25` |
| `IOT-*` findings | `10` | `10` | `9` |
| IoT Hubs observed | `1` | `1` | `1` |
| Device identities observed | `1` | `1` | `3` |
| Shared access policies | `5` | `6` | `5` |
| Overbroad shared access policies | `1` | `2` | `1` |
| Diagnostic destinations | `1` | `0` | `1` |
| Defender for IoT observed | `False` | `False` | `False` |
| Public network IoT Hubs | `1` | `1` | `1` |
| Private endpoints | `0` | `0` | `0` |
| IoT alert rules | `0` | `0` | `1` |

## Triggered IoMT Controls

| Control | Weak IoMT baseline | Simulated clinic | Interpretation |
| --- | --- | --- | --- |
| `IOT-001` Device identity authentication evidence | Triggered | Triggered | Shared-key device identities and incomplete strong-authentication evidence remain visible in both runs. |
| `IOT-002` Shared access policy least privilege | Triggered | Triggered | Both runs include overbroad or default shared-access policy exposure. |
| `IOT-003` Diagnostic logging | Triggered | Triggered | Weak baseline has no diagnostic destination. Simulated clinic has diagnostics, but still leaves category/retention evidence gaps. |
| `IOT-004` Defender/security monitoring | Triggered | Triggered | Defender for IoT or equivalent security monitoring was not observed. |
| `IOT-005` Public network access | Triggered | Triggered | Both scenarios expose IoT Hub over public network access. |
| `IOT-006` Private endpoint coverage | Triggered | Triggered | No private endpoint coverage was observed for sensitive IoMT telemetry paths. |
| `IOT-007` Telemetry routing and retention | Triggered | Triggered | Routing and retention evidence remains incomplete. |
| `IOT-008` Secret governance | Triggered | Triggered | IoT credential governance was not linked to managed secret rotation evidence. |
| `IOT-009` Clinical alert routing | Triggered | Not triggered | The simulated clinic added an IoT metric alert; the weak baseline did not. |
| `IOT-010` Clinical-operational ownership boundary | Triggered | Triggered | Human validation is still required for clinical-operational responsibility boundaries. |

## Result Summary

The controlled runs support the central CRIS-IoMT claim: cloud control-plane telemetry can expose meaningful healthcare IoT governance weaknesses without inspecting patient data, clinical telemetry payloads, device firmware, or radio/sensing layers.

The weak baseline and simulated clinic both produced deterministic IoMT findings, but the simulated clinic showed an expected reduction in one operational-monitoring finding after adding an IoT-specific alert rule. This is a useful early signal that CRIS-IoMT can distinguish between deliberately weak and more operationally mature cloud-connected healthcare IoT configurations.

The results should not be reported as evidence of full healthcare IoT security. They are evidence of cloud-side governance posture only.
