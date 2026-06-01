# Paper Summary

## Working Title

**CRIS-IoMT: Evidence-Driven Cloud Governance Assessment for Cloud-Connected Healthcare IoT Systems**

## Abstract

Healthcare IoT and Internet of Medical Things deployments increasingly depend on cloud services for device identity, telemetry ingestion, logging, monitoring, key management, storage, and incident investigation. Existing healthcare IoT security work often focuses on devices, sensing, wireless communications, firmware, or anomaly detection, while the cloud governance layer remains less systematically assessed. CRIS-IoMT converts Azure IoT Hub and related cloud control-plane telemetry into deterministic, traceable healthcare IoT governance findings. It evaluates ten IoMT controls across device identity, shared access policies, diagnostics, security monitoring, public exposure, private endpoint coverage, telemetry governance, secret management, alert routing, and clinical-operational ownership boundaries. The system explicitly separates cloud-observable evidence from device, endpoint, clinical, and human-verification evidence that remains outside cloud observability.

## Research Gap

The gap addressed by CRIS-IoMT is the intersection of four properties:

1. Healthcare IoT cloud-governance scope.
2. Deterministic evidence-to-control decisions.
3. Explicit evidence-sufficiency boundaries for cloud, device, endpoint, clinical, and human-review evidence.
4. Candidate NHS DSPT 2025-26 CAF-aligned and NCSC CAF-oriented mappings for expert review.

## Contributions

1. A cloud-side evidence model for healthcare IoT assurance.
2. A deterministic Azure-first IoMT control catalogue with ten `IOT-*` controls.
3. An evidence-sufficiency boundary separating cloud evidence from device, clinical, endpoint, and human-review evidence.
4. Candidate NHS DSPT 2025-26 CAF-aligned outcome mappings and NCSC CAF-oriented readiness themes.
5. A controlled Azure lab methodology for weak, simulated-clinic, and hardened-clinic healthcare IoT architectures.
6. JSON and Markdown IoMT evidence packs for reviewer-ready reporting.

## Evaluation Summary

The first evaluation uses controlled Azure IoT Hub labs in `uaenorth`.

| Scenario | IoMT findings | Healthcare IoT score | Key observation |
| --- | ---: | ---: | --- |
| Weak IoMT baseline | `10` | `26.64` | Public IoT Hub access, no telemetry route, no IoT alert rule. |
| Simulated clinic | `9` | `27.32` | Alerting added, but public exposure and telemetry-governance gaps remain. |
| Hardened clinic | `7` | `24.92` | Public access disabled, storage route added, IoT alerting observed. |

The strongest controlled result is that `IOT-005`, `IOT-007`, and `IOT-009` changed as expected when the hardened clinic disabled public access, added telemetry routing, and deployed a real Azure Monitor alert rule.

## Intended Venues

Potential venues include IEEE JBHI, IEEE Sensors, IEEE IoT Journal, HealthCom, Computers & Security, or a healthcare cyber-physical systems workshop. The best venue depends on how strongly the paper is positioned around healthcare IoT assurance, cloud governance, sensing infrastructure, and clinical-operational boundaries.

