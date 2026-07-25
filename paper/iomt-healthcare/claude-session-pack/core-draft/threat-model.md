# CRIS-IoMT Threat Model and Assurance Boundary

## Purpose

This document defines what CRIS-IoMT is designed to assess, what it deliberately excludes, and which claims can be made from cloud control-plane evidence.

The central boundary is:

> CRIS-IoMT assesses cloud-side governance failures in healthcare IoT systems. It does not assess physiological sensing correctness, device firmware compromise, radio-layer security, clinical safety, or medical-device certification.

## System Model

CRIS-IoMT models a cloud-connected healthcare IoT environment in which:

- healthcare IoT devices or gateways connect to a cloud IoT ingestion service
- device identities are registered and authenticated through cloud services
- telemetry is routed, retained, monitored, or exported through cloud services
- operational teams rely on cloud logs, alerts, keys, policies, and resource configuration for investigation and governance
- healthcare, security, and operational stakeholders need evidence about cloud-side assurance posture

The first implementation uses Azure IoT Hub as the cloud IoT service under assessment.

## Assets In Scope

CRIS-IoMT treats the following as in-scope cloud-side assets:

- IoT Hub device identity registry
- IoT Hub shared access policies
- IoT Hub public network access and private endpoint posture
- IoT Hub diagnostic settings
- IoT Hub telemetry routing and retention configuration
- Azure Monitor alert rules and action groups linked to IoT operations
- Defender for IoT or equivalent cloud security monitoring observability
- linked storage, Key Vault, logging, and governance resources
- report evidence, finding lineage, and assurance pack outputs

## Assets Out Of Scope

The following are explicitly outside CRIS-IoMT's assessment boundary:

- patient data and clinical telemetry payload content
- physiological sensing accuracy
- medical-device safety and clinical safety cases
- device firmware integrity
- embedded operating-system security
- wireless, RF, Bluetooth, Zigbee, or proprietary sensing protocols
- hospital endpoint or mobile-device posture unless separately integrated
- biomedical engineering maintenance records
- clinical operating procedures except as human-supplied evidence

## Adversary and Failure Model

CRIS-IoMT does not model only a single external attacker. It models cloud-side assurance failure modes that can arise from attackers, administrators, procurement drift, operational shortcuts, or missing evidence.

In-scope failure modes include:

- public IoT ingestion endpoints left open by default
- broad shared access policies that violate least privilege
- weak or insufficiently evidenced device identity posture
- missing diagnostic logging for healthcare IoT investigation
- missing operational alert routing for clinical IoT events
- missing private endpoint coverage for sensitive telemetry paths
- cloud credentials not linked to managed secret governance
- unavailable or unlicensed security-monitoring evidence
- lack of documented clinical-operational ownership boundary
- governance drift between intended and deployed cloud posture

Out-of-scope adversary capabilities include:

- exploiting medical-device firmware vulnerabilities directly
- manipulating sensor readings at the physical layer
- attacking radio or body-area-network protocols
- compromising patient records outside the cloud control-plane scope
- validating whether a clinical intervention is safe or unsafe

## Evidence Classes

CRIS-IoMT separates evidence into the following classes:

| Evidence class | Meaning | Example |
| --- | --- | --- |
| Direct cloud evidence | Observed directly through Azure APIs or CLI commands. | IoT Hub public network access is enabled. |
| Inferred cloud evidence | Derived from relationships among observed resources. | Private endpoint coverage is expected because IoMT telemetry services are present. |
| Unavailable cloud evidence | Relevant cloud signal exists but cannot be observed because of permissions, licensing, or API limits. | Defender for IoT posture cannot be confirmed. |
| Device or endpoint evidence required | Cloud evidence is insufficient; device, MDM, EDR, firmware, or endpoint data is needed. | Whether a physical device is patched or running approved firmware. |
| Clinical or operational evidence required | Human-held evidence is needed. | Whether responsibility between clinical and IT teams is formally documented. |

## Allowed Claims

CRIS-IoMT can support claims such as:

- a cloud IoT Hub was observed in the assessment scope
- the IoT Hub has public network access enabled or disabled
- diagnostic settings were observed or absent
- device identities were observable in cloud inventory
- broad shared access policies were observed
- IoT alert rules were observed or absent
- private endpoint coverage was missing or present for observed cloud services
- Defender/security monitoring evidence was observed, absent, or unavailable
- a finding was generated deterministically from a stated evidence field
- an evidence gap requires human, clinical, endpoint, or device validation

## Forbidden Claims

CRIS-IoMT must not claim:

- the healthcare IoT system is clinically safe
- the medical devices are secure
- device firmware is free of vulnerabilities
- patient data is protected end to end
- NHS DSPT or NCSC CAF compliance is certified
- Cyber Essentials compliance is certified
- the organisation is safe from healthcare IoT cyber incidents
- cloud evidence is sufficient to replace clinical safety review or biomedical engineering validation

## Assurance Boundary Statement

Recommended wording for the paper:

> CRIS-IoMT provides deterministic assurance over the cloud governance layer of healthcare IoT systems. Its findings are valid only for cloud-observable control-plane evidence and explicitly preserve the boundary around patient data, device firmware, clinical safety, biomedical sensing, and human operational evidence.

## Implications for Evaluation

The controlled Azure labs should be evaluated as cloud-governance experiments, not as healthcare device experiments. A successful CRIS-IoMT run demonstrates that the tool can detect cloud-side posture differences between scenarios. It does not demonstrate complete healthcare IoT security coverage.

For this reason, evaluation metrics should include:

- number of cloud-observable IoMT controls triggered
- evidence sufficiency class distribution
- scenario-specific IoT Hub evidence counts
- manual evidence backlog
- reviewer judgment on whether boundaries are clearly communicated

## Reviewer Risk

The most likely reviewer criticism is overclaiming. The answer is to foreground the boundary:

- The paper is not about replacing device security testing.
- The paper is not about certifying clinical safety.
- The contribution is a deterministic, evidence-sufficiency-aware cloud governance layer for healthcare IoT assurance.

This framing makes the work stronger because it explains exactly where cloud telemetry helps and where it cannot.
