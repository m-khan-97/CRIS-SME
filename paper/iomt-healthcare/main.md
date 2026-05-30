# CRIS-IoMT: Evidence-Driven Cloud Governance Assessment for Cloud-Connected Healthcare IoT Systems

## Abstract

Healthcare IoT and Internet of Medical Things deployments increasingly depend on cloud services for device identity, telemetry ingestion, logging, monitoring, key management, storage, and incident investigation. Existing healthcare IoT security work often focuses on devices, sensing, wireless communications, firmware, or anomaly detection, while the cloud governance layer remains less systematically assessed. This paper presents CRIS-IoMT, an evidence-driven extension of CRIS that converts Azure IoT Hub and related cloud control-plane telemetry into deterministic, traceable healthcare IoT governance findings. CRIS-IoMT evaluates ten IoMT controls across device identity, shared access policies, diagnostics, security monitoring, public exposure, private endpoint coverage, telemetry governance, secret management, alert routing, and clinical-operational ownership boundaries. The system explicitly separates cloud-observable evidence from device, endpoint, clinical, and human-verification evidence that remains outside cloud observability. We evaluate CRIS-IoMT using controlled Azure healthcare IoT labs, including an intentionally weak baseline and a simulated clinic architecture. The results show that cloud control-plane evidence can identify meaningful IoMT governance weaknesses without inspecting patient data, clinical telemetry payloads, firmware, or sensing channels, while preserving explicit limitations around medical-device security and clinical safety.

## 1. Introduction

Cloud-connected healthcare IoT systems are not only collections of devices and sensors. They also rely on cloud services that authenticate devices, receive telemetry, route messages, retain logs, raise alerts, store data, and support incident investigation. Weaknesses in these services can affect the assurance posture of the healthcare IoT environment even when the physical device layer is outside the scope of assessment.

CRIS-IoMT addresses this governance layer. It extends CRIS from SME cloud governance into healthcare IoT cloud assurance by evaluating cloud-observable IoT evidence and preserving the boundary around evidence that requires device, firmware, endpoint, clinical, or operational validation.

## 2. Contributions

This paper contributes:

1. A cloud-side evidence model for healthcare IoT assurance.
2. A deterministic Azure-first IoMT control catalogue with ten `IOT-*` controls.
3. An evidence-sufficiency boundary that distinguishes cloud-observable findings from device, endpoint, clinical, and human-verification gaps.
4. A candidate mapping from IoMT controls to NHS DSPT 2025-26 CAF-aligned outcome IDs and NCSC CAF-oriented readiness themes.
5. A controlled Azure lab methodology for weak and simulated-clinic healthcare IoT architectures.
6. JSON and Markdown IoMT evidence packs for reviewer-ready reporting.

## 3. Research Questions

RQ1. Which healthcare IoT assurance claims can be supported from cloud control-plane evidence alone?

RQ2. Which IoMT risks remain outside cloud observability and require device, endpoint, network, clinical, or operational evidence?

RQ3. Can deterministic IoMT controls identify deliberately weak cloud-connected healthcare IoT configurations in controlled Azure labs?

RQ4. How do scenario-level IoMT findings differ between weak and more operationally mature simulated healthcare IoT architectures?

RQ5. Can evidence-pack reporting make the boundary between cloud evidence and clinical/device evidence clear to reviewers?

## 4. Related Work and Positioning

CRIS-IoMT sits between healthcare IoT security research, cloud security posture management, IoT/OT monitoring products, and UK healthcare assurance frameworks. Existing systems address important parts of this space. Microsoft Defender for IoT focuses on IoT/OT monitoring and threat detection. Microsoft Defender for Cloud provides cloud security posture management and regulatory-compliance views. AWS IoT Device Defender audits and monitors AWS IoT device fleets. Commercial CNAPP and CSPM platforms such as Wiz and Prisma Cloud provide broad agentless cloud inventory, graph-based context, compliance, and risk prioritisation. OT visibility tools such as Cisco Cyber Vision focus on industrial and operational-network visibility. NHS DSPT and NCSC CAF provide assurance structures and outcomes rather than live cloud evidence collection.

CRIS-IoMT's research contribution is narrower. It asks whether cloud control-plane evidence can be converted into deterministic healthcare IoT governance findings while preserving the boundary around device, endpoint, clinical, and human-verification evidence.

| System or framework | Primary scope | Healthcare IoT specificity | Cloud evidence | Explicit evidence boundary | DSPT/CAF-oriented output | Open research artifact |
|---|---|---:|---:|---:|---:|---:|
| CRIS-IoMT | Healthcare IoT cloud governance | High | High | Yes | Candidate mapping | Yes |
| Defender for IoT | IoT/OT monitoring and detection | Medium to high | Medium | Product-dependent | Not primary framing | No |
| Defender for Cloud | CSPM and cloud compliance | Low to medium | High | Product-dependent | Broad compliance | No |
| AWS IoT Device Defender | AWS IoT fleet auditing and monitoring | Medium | High for AWS IoT | Product-dependent | No NHS-specific mapping | No |
| Wiz / Prisma-style CSPM | Cloud risk prioritisation and compliance | Low to medium | High | Product-dependent | Broad compliance | No |
| Cisco Cyber Vision-style OT visibility | Industrial and OT network visibility | Medium | Low to medium | Product-dependent | Not cloud-governance specific | No |
| NHS DSPT / NCSC CAF | Assurance outcomes and self-assessment | High | None by itself | Guidance-driven | Native assurance target | Public guidance, not live evidence tooling |

The novelty claim is therefore deliberately bounded: our review of official product and framework materials did not identify an open, reproducible artifact that combines healthcare IoT cloud-governance scope, deterministic evidence-to-control decisions, explicit evidence-sufficiency boundaries, and candidate NHS DSPT 2025-26 CAF-aligned plus NCSC CAF-oriented mapping. The fuller comparison is recorded in `related-work.md`.

## 5. System Overview

CRIS-IoMT extends the CRIS pipeline:

1. The Azure collector discovers IoT Hub resources and related cloud services.
2. The IoMT evidence model normalizes IoT Hub posture into deterministic fields.
3. Ten `IOT-*` controls evaluate identity, shared-access policy, diagnostics, monitoring, exposure, private endpoint, routing, retention, secret governance, alerting, and clinical-operational boundary evidence.
4. Findings flow through deterministic CRIS scoring, evidence lineage, provisional IoMT confidence calibration, and reporting.
5. IoMT evidence packs summarize cloud-observable findings and manual evidence gaps.

## 6. Threat Model and Assurance Boundary

The threat model is described in `threat-model.md`. CRIS-IoMT models cloud-side governance failures in healthcare IoT environments, including public IoT ingestion exposure, overbroad shared access policies, weakly evidenced device identity posture, missing diagnostics, missing alerting, missing private endpoint coverage, unavailable security-monitoring evidence, and undocumented clinical-operational ownership boundaries.

The adversary model is intentionally broader than an external attacker. It includes governance drift, misconfiguration, incomplete evidence, operational shortcuts, and weak assurance boundaries. This is important because many healthcare IoT risks emerge not from a novel device exploit but from the cloud services that authenticate, ingest, route, monitor, and retain evidence for connected devices.

The assurance boundary is strict. CRIS-IoMT does not assess physiological sensing correctness, device firmware integrity, wireless protocol security, patient data content, or clinical safety. It can support cloud-observable assurance claims, but it must not claim that a healthcare IoT system is clinically safe, medically certified, or fully secure.

Allowed claims include statements such as whether IoT Hub public access, shared access policies, diagnostic settings, alert rules, private endpoint posture, and security-monitoring observability were detected in the assessment scope. Forbidden claims include NHS DSPT certification, NCSC CAF certification, medical-device security certification, clinical safety approval, or end-to-end patient data protection.

NHS DSPT references in this paper are candidate mappings to the 2025-26 CAF-aligned outcome structure, such as `B2.a` for identity verification, authentication and authorisation, `C1.a` for monitoring coverage, and `D1.a` for response planning. They are included to support expert review and readiness discussion, not to assert DSPT compliance.

## 7. Methodology

The methodology is described in `methodology.md`. In summary, CRIS-IoMT uses Azure control-plane evidence and explicitly avoids patient data, clinical payloads, firmware inspection, radio protocol testing, and medical-device certification claims.

## 8. Evaluation

The first evaluation uses controlled Azure IoT Hub labs in `uaenorth`:

- weak IoMT baseline
- simulated clinic
- hardened clinic
- retained clean standing demo for browser demonstration and collector validation

The weak, simulated-clinic, and hardened-clinic assessments use resource-group scoped collection to isolate scenario resources from other subscription assets.

Healthcare IoT findings are reported as an optional standalone category. The base CRIS SME overall score currently assigns the `IOT` category a weight of `0.0`, so IoMT findings do not change the standard SME overall risk score; the Healthcare IoT category score is reported separately for research evaluation.

## 9. Results

Detailed results are recorded in `evaluation-results.md`.

Key results:

- Weak IoMT baseline: 10 `IOT-*` findings, Healthcare IoT score `26.64`.
- Simulated clinic: 9 `IOT-*` findings, Healthcare IoT score `27.32`.
- Hardened clinic: 7 `IOT-*` findings, Healthcare IoT score `24.92`.
- The simulated clinic included diagnostics and an alert rule, removing `IOT-009` compared with the weak baseline.
- The hardened clinic disabled IoT Hub public network access and added storage routing, removing `IOT-005` and `IOT-007` in addition to `IOT-009`.
- The scenarios still retain meaningful findings around overbroad shared access policies, missing private endpoints, Defender for IoT observability, secret governance, and clinical-operational ownership boundaries.

The most important controlled differences are now `IOT-005`, `IOT-007`, and `IOT-009`: the weak baseline had public IoT Hub access, no telemetry route, and no IoT alert rule; the hardened clinic disabled public access, added a storage route, and deployed a real Azure Monitor metric alert. These results are the clearest early evidence that CRIS-IoMT reflects controlled cloud-side configuration differences across multiple IoMT governance controls.

## 10. Discussion

The results support the paper's central argument: cloud-side governance evidence can identify a meaningful subset of healthcare IoT assurance weaknesses without touching patient data or device firmware. The results also show why cloud evidence must be carefully bounded. A cloud report cannot certify clinical safety, device security, firmware integrity, or sensing reliability.

The strongest framing is therefore not automation of healthcare IoT certification. It is evidence-sufficiency-aware pre-assessment of the cloud governance layer that supports healthcare IoT operations.

`IOT-004` should be interpreted especially carefully. In the Azure for Students evaluation context, Defender for IoT was not observable in any scenario. The resulting finding is therefore a structural monitoring-evidence gap: CRIS-IoMT did not observe Defender for IoT or equivalent cloud security monitoring evidence. It is not proof that a healthcare organisation has no compensating monitoring outside the assessed Azure control plane.

## 11. Threats to Validity

The evaluation currently uses controlled Azure labs, not production NHS environments. The scenarios are intentionally simplified and do not include real clinical devices, patient telemetry, biomedical instrumentation, or operational healthcare workflows. Azure IoT Hub evidence may not generalize directly to AWS IoT Core, Google Cloud IoT alternatives, on-premises gateways, or hybrid medical device networks.

The scoring model is deterministic, but control weights and confidence values still require broader empirical calibration. IoMT controls are marked as provisional using the three scenario-scoped lab runs as early calibration evidence. The current live runs demonstrate feasibility and signal separation between scenarios, not complete validation of healthcare IoT assurance.

## 12. Limitations

CRIS-IoMT does not inspect patient data, clinical telemetry payloads, device firmware, wireless channels, physical sensors, or endpoint agents. It does not certify NHS DSPT, NCSC CAF, CE, medical-device safety, or clinical safety cases.

The Azure collector depends on available permissions and API support. Defender for IoT and some tenant-level security signals may be unavailable or only partially observable. Resource-group scoped evaluation improves scenario isolation, but production deployments may require more complex scoping logic for shared services.

## 13. Future Work

Future work should include:

- a stronger clean baseline with private endpoint coverage
- synthetic telemetry routing to storage or Event Hub
- endpoint/MDM integration for device-side evidence
- Defender for IoT integration where licensed and available
- AWS IoT Core and Google Cloud equivalents
- clinician, biomedical engineer, or healthcare security reviewer study
- broader empirical calibration across multiple healthcare-like tenants
- stronger NHS DSPT and NCSC CAF mapping review with domain experts

## 14. Conclusion

CRIS-IoMT demonstrates that cloud control-plane evidence can support deterministic, explainable assurance of the cloud governance layer behind healthcare IoT systems. The contribution is not certification and not device security testing. Its value is making cloud-observable IoMT risks and non-observable clinical/device evidence boundaries explicit, traceable, and reviewable.
