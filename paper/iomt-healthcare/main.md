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
4. A mapping from IoMT controls to NHS DSPT and NCSC CAF-oriented readiness themes.
5. A controlled Azure lab methodology for weak and simulated-clinic healthcare IoT architectures.
6. JSON and Markdown IoMT evidence packs for reviewer-ready reporting.

## 3. Research Questions

RQ1. Which healthcare IoT assurance claims can be supported from cloud control-plane evidence alone?

RQ2. Which IoMT risks remain outside cloud observability and require device, endpoint, network, clinical, or operational evidence?

RQ3. Can deterministic IoMT controls identify deliberately weak cloud-connected healthcare IoT configurations in controlled Azure labs?

RQ4. How do scenario-level IoMT findings differ between weak and more operationally mature simulated healthcare IoT architectures?

RQ5. Can evidence-pack reporting make the boundary between cloud evidence and clinical/device evidence clear to reviewers?

## 4. System Overview

CRIS-IoMT extends the CRIS pipeline:

1. The Azure collector discovers IoT Hub resources and related cloud services.
2. The IoMT evidence model normalizes IoT Hub posture into deterministic fields.
3. Ten `IOT-*` controls evaluate identity, shared-access policy, diagnostics, monitoring, exposure, private endpoint, routing, retention, secret governance, alerting, and clinical-operational boundary evidence.
4. Findings flow through deterministic CRIS scoring, evidence lineage, confidence, and reporting.
5. IoMT evidence packs summarize cloud-observable findings and manual evidence gaps.

## 5. Methodology

The methodology is described in `methodology.md`. In summary, CRIS-IoMT uses Azure control-plane evidence and explicitly avoids patient data, clinical payloads, firmware inspection, radio protocol testing, and medical-device certification claims.

## 6. Evaluation

The first evaluation uses controlled Azure IoT Hub labs in `uaenorth`:

- weak IoMT baseline
- simulated clinic
- retained clean standing demo for browser demonstration and collector validation

The weak and simulated-clinic assessments use resource-group scoped collection to isolate scenario resources from other subscription assets.

## 7. Results

Detailed results are recorded in `evaluation-results.md`.

Key results:

- Weak IoMT baseline: 10 `IOT-*` findings, Healthcare IoT score `26.64`.
- Simulated clinic: 9 `IOT-*` findings, Healthcare IoT score `27.32`.
- The simulated clinic included diagnostics and an alert rule, removing `IOT-009` compared with the weak baseline.
- Both scenarios retained meaningful findings around public IoT Hub exposure, overbroad shared access policies, missing private endpoints, Defender for IoT observability, telemetry governance, secret governance, and clinical-operational ownership boundaries.

## 8. Discussion

The results support the paper's central argument: cloud-side governance evidence can identify a meaningful subset of healthcare IoT assurance weaknesses without touching patient data or device firmware. The results also show why cloud evidence must be carefully bounded. A cloud report cannot certify clinical safety, device security, firmware integrity, or sensing reliability.

The strongest framing is therefore not automation of healthcare IoT certification. It is evidence-sufficiency-aware pre-assessment of the cloud governance layer that supports healthcare IoT operations.

## 9. Threats to Validity

The evaluation currently uses controlled Azure labs, not production NHS environments. The scenarios are intentionally simplified and do not include real clinical devices, patient telemetry, biomedical instrumentation, or operational healthcare workflows. Azure IoT Hub evidence may not generalize directly to AWS IoT Core, Google Cloud IoT alternatives, on-premises gateways, or hybrid medical device networks.

The scoring model is deterministic, but control weights and confidence values still require broader empirical calibration. The current live runs demonstrate feasibility and signal separation between scenarios, not complete validation of healthcare IoT assurance.

## 10. Limitations

CRIS-IoMT does not inspect patient data, clinical telemetry payloads, device firmware, wireless channels, physical sensors, or endpoint agents. It does not certify NHS DSPT, NCSC CAF, CE, medical-device safety, or clinical safety cases.

The Azure collector depends on available permissions and API support. Defender for IoT and some tenant-level security signals may be unavailable or only partially observable. Resource-group scoped evaluation improves scenario isolation, but production deployments may require more complex scoping logic for shared services.

## 11. Future Work

Future work should include:

- a stronger clean baseline with private endpoint coverage
- synthetic telemetry routing to storage or Event Hub
- endpoint/MDM integration for device-side evidence
- Defender for IoT integration where licensed and available
- AWS IoT Core and Google Cloud equivalents
- clinician, biomedical engineer, or healthcare security reviewer study
- broader empirical calibration across multiple healthcare-like tenants
- stronger NHS DSPT and NCSC CAF mapping review with domain experts

## 12. Conclusion

CRIS-IoMT demonstrates that cloud control-plane evidence can support deterministic, explainable assurance of the cloud governance layer behind healthcare IoT systems. The contribution is not certification and not device security testing. Its value is making cloud-observable IoMT risks and non-observable clinical/device evidence boundaries explicit, traceable, and reviewable.
