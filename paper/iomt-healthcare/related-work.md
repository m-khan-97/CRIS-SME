# Related Work and Positioning

This note positions CRIS-IoMT against adjacent commercial platforms, cloud-native security services, healthcare assurance frameworks, and healthcare IoT research. The purpose is not to claim that CRIS-IoMT replaces these systems. The purpose is to identify the narrower research gap addressed by this paper: deterministic, evidence-sufficiency-aware assessment of the cloud governance layer behind healthcare IoT deployments.

## Positioning Statement

CRIS-IoMT is not a medical-device security scanner, not an OT network sensor, not a clinical safety case, and not an NHS DSPT or NCSC CAF certification tool. It is a research prototype that turns Azure IoT Hub and related cloud control-plane evidence into traceable healthcare IoT governance findings, while explicitly recording which assurance claims remain outside cloud observability.

This boundary is the main novelty. Existing systems provide valuable device discovery, posture management, monitoring, compliance management, or assurance guidance, but they do not normally expose a paper-grade evidence boundary that says which healthcare IoT claims are directly supported by cloud telemetry, which are inferred, and which require endpoint, device, clinical, or human review.

## Comparison Matrix

| System or framework | Primary scope | Healthcare IoT specificity | Cloud control-plane evidence | Evidence-sufficiency boundary | DSPT/CAF readiness mapping | Deterministic reviewer-ready outputs | Open/reproducible artifact |
|---|---|---:|---:|---:|---:|---:|---:|
| CRIS-IoMT | Healthcare IoT cloud governance evidence | High | High | Explicit | Candidate mapping | Yes | Yes |
| Microsoft Defender for IoT | OT/IoT asset discovery, monitoring, and threat detection | Medium to high | Medium | Product-dependent | Not its primary published framing | Product reports | No |
| Microsoft Defender for Cloud | CSPM, cloud security posture, regulatory compliance, workload protection | Low to medium | High | Product-dependent | Broad compliance, not IoMT-specific | Product reports | No |
| AWS IoT Device Defender | AWS IoT fleet auditing, detect rules, and abnormal behavior monitoring | Medium | High for AWS IoT | Product-dependent | No NHS-specific mapping in the base service | Product reports | No |
| Wiz / Prisma-style CNAPP and CSPM platforms | Agentless cloud posture, graph context, compliance, risk prioritization | Low to medium | High | Product-dependent | Broad compliance, not IoMT-specific | Product reports | No |
| Cisco Cyber Vision / OT visibility tools | Industrial and OT network visibility, asset discovery, anomaly detection | Medium for connected clinical/industrial networks | Low to medium | Product-dependent | Not cloud-governance specific | Product reports | No |
| NHS DSPT and NCSC CAF | Assurance framework and self-assessment structure | High for UK healthcare/CNI assurance | None by itself | Guidance-driven | Native assurance target | Manual/self-assessment outputs | Public guidance, not live evidence tooling |
| Academic IoMT security frameworks | Device, firmware, wireless, sensing, privacy, ML, anomaly detection | High | Usually low | Usually implicit | Rarely mapped to DSPT/CAF | Varies | Varies |

## What Existing Tooling Does Well

Microsoft Defender for IoT is strong in IoT and OT monitoring contexts, particularly for asset discovery, network monitoring, and security operations workflows. It is therefore a complementary source of monitoring evidence for CRIS-IoMT rather than a competitor in the narrow research sense. In the current Azure for Students evaluation environment, Defender for IoT was not observable, so `IOT-004` is reported as a monitoring-evidence gap rather than proof that monitoring is absent.

Microsoft Defender for Cloud is a mature CSPM and cloud security platform. It provides posture management, recommendations, secure score, and regulatory-compliance views for cloud assets. CRIS-IoMT differs by narrowing the problem to healthcare IoT cloud governance and by emitting deterministic, research-auditable evidence packs with explicit clinical/device evidence boundaries.

AWS IoT Device Defender provides auditing and monitoring capabilities for AWS IoT device fleets. It is highly relevant future work for a multi-cloud CRIS-IoMT extension, but it does not address the Azure IoT Hub evidence path evaluated in this paper, nor does it provide the NHS DSPT/CAF-oriented evidence-pack framing used here.

Commercial CNAPP and CSPM platforms such as Wiz and Prisma Cloud are strong at agentless cloud inventory, graph context, compliance, and cloud risk prioritization. CRIS-IoMT does not try to compete with their breadth. Its contribution is a smaller, open, deterministic control model for healthcare IoT cloud assurance with explicit evidence sufficiency.

OT and industrial IoT visibility products such as Cisco Cyber Vision provide asset discovery and network security visibility for connected operational environments. These tools are closer to the device and network-observation layer, while CRIS-IoMT focuses on cloud governance evidence from services such as IoT Hub, diagnostics, routing, storage, key management, and alerting.

NHS DSPT and NCSC CAF define assurance expectations and outcomes, but they do not themselves collect Azure IoT Hub evidence, score findings, or generate cloud evidence packs. CRIS-IoMT should therefore be presented as a pre-assessment and evidence-organisation layer for expert review, not as an assurance authority.

## Research Gap

The gap addressed by CRIS-IoMT is the intersection of four properties:

1. Healthcare IoT cloud-governance scope.
2. Deterministic evidence-to-control decisions.
3. Explicit evidence-sufficiency boundaries for cloud, device, endpoint, clinical, and human-review evidence.
4. Candidate NHS DSPT 2025-26 CAF-aligned and NCSC CAF-oriented mappings for expert review.

Our review of official product and framework materials did not identify an open, reproducible artifact that combines all four properties. This is the careful novelty claim the paper should preserve.

## Suggested Paper Wording

> CRIS-IoMT complements existing IoT security, CSPM, and assurance frameworks by focusing on a narrower but under-specified layer: cloud control-plane governance evidence for healthcare IoT deployments. Unlike commercial posture-management products, the prototype is open, deterministic, and designed for research inspection. Unlike healthcare assurance frameworks, it collects and classifies live cloud evidence. Unlike device-centric IoMT research, it explicitly avoids firmware, sensing, wireless, and clinical-safety claims, and instead records the boundary between cloud-observable evidence and evidence requiring clinical, endpoint, or device validation.

## Sources Used for Positioning

- Microsoft Defender for IoT documentation: https://learn.microsoft.com/azure/defender-for-iot/
- Microsoft Defender for IoT overview: https://learn.microsoft.com/en-us/azure/defender-for-iot/organizations/overview
- Microsoft Defender for Cloud CSPM documentation: https://learn.microsoft.com/en-us/azure/defender-for-cloud/concept-cloud-security-posture-management
- AWS IoT Device Defender documentation: https://docs.aws.amazon.com/iot-device-defender/
- NCSC Cyber Assessment Framework: https://www.ncsc.gov.uk/collection/cyber-assessment-framework
- NHS Data Security and Protection Toolkit: https://dsptoolkit.nhs.uk/
- Wiz CSPM positioning: https://www.wiz.io/solutions/cspm
- Palo Alto Networks Prisma Cloud CSPM positioning: https://www.paloaltonetworks.com/prisma/cloud/cloud-security-posture-management
- Cisco Cyber Vision product page: https://www.cisco.com/c/en/us/products/security/cyber-vision/index.html
