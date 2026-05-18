# CRIS-IoMT Paper Plan

Working title:

**CRIS-IoMT: Evidence-Driven Cloud Governance Assessment for Cloud-Connected Healthcare IoT Systems**

Alternative title:

**Deterministic Assurance of Cloud-Connected Healthcare IoT Environments from Cloud Control-Plane Evidence**

## One-Sentence Claim

CRIS-IoMT shows that healthcare IoT assurance can be strengthened by converting cloud-side IoT control-plane evidence into deterministic, traceable findings and healthcare-readiness claims, while preserving explicit boundaries around patient data, device firmware, clinical safety, and human verification.

## Research Gap

Healthcare IoT security research often focuses on devices, sensing, wireless communication, biomedical instrumentation, network protocols, firmware, or anomaly detection. These are essential, but they leave a practical governance gap.

Modern healthcare IoT deployments also depend on cloud services:

- device identity registries
- IoT message brokers and ingestion endpoints
- telemetry routing
- diagnostic logs
- storage accounts and data lakes
- key management
- private endpoints and network isolation
- security monitoring
- incident evidence retention

Security failures in these services can undermine healthcare IoT assurance even when devices and sensing components are well designed. Yet cloud governance evidence is rarely converted into deterministic, healthcare-specific assurance outputs.

## Core Contribution

This paper contributes:

1. A cloud-side evidence model for healthcare IoT assurance.
2. A deterministic IoMT control catalogue for Azure-first cloud-connected healthcare IoT environments.
3. An evidence sufficiency taxonomy that distinguishes observed cloud evidence, inferred posture, unavailable cloud signals, endpoint/device evidence, and clinical/operational confirmation.
4. A mapping from IoMT cloud controls to NHS DSPT and NCSC CAF readiness themes.
5. A controlled Azure healthcare IoT lab methodology that evaluates clean, weak, and realistic simulated architectures without patient data.
6. A reporting workflow that produces technical findings, executive summaries, assurance caveats, and reviewer-ready evidence packs.

## Research Questions

RQ1. Which healthcare IoT assurance claims can be supported from cloud control-plane evidence alone?

RQ2. Which IoMT risks remain outside cloud observability and require device, endpoint, network, clinical, or operational evidence?

RQ3. How effectively can deterministic IoMT controls identify deliberately weak cloud-connected healthcare IoT configurations in controlled Azure labs?

RQ4. How well do CRIS-IoMT findings map to NHS DSPT and NCSC CAF readiness themes?

RQ5. Can evidence-sufficiency-aware reporting help reviewers distinguish real cloud-side risk from observability gaps and clinical-safety boundaries?

## System Scope

The first implementation should be Azure-first because Azure IoT Hub is a mature, inspectable cloud service and fits the existing CRIS-SME collector architecture.

Initial evidence sources:

- Azure IoT Hub inventory
- IoT Hub network access configuration
- IoT Hub diagnostic settings
- IoT Hub shared access policies
- IoT Hub device identity counts and authentication metadata where available
- Defender for IoT or Microsoft Defender cloud security signals where accessible
- private endpoint coverage
- storage, Key Vault, monitoring, and governance evidence already collected by CRIS-SME

Out of scope:

- patient data payload inspection
- clinical telemetry content analysis
- firmware reverse engineering
- wireless protocol testing
- radio-frequency sensing validation
- medical device certification
- clinical safety case approval

## Architecture

CRIS-IoMT extends the existing CRIS pipeline:

1. Azure collector gathers standard cloud governance evidence.
2. Azure IoT evidence collector gathers IoT Hub and connected-service posture.
3. IoMT evidence model normalizes healthcare IoT signals into deterministic fields.
4. `IOT-*` controls evaluate identity, ingestion, network, logging, monitoring, retention, and evidence sufficiency.
5. Findings flow into the existing CRIS scoring, evidence lineage, confidence, reporting, and review layers.
6. NHS DSPT and NCSC CAF mapping generates healthcare-readiness outputs with caveats.

## Evaluation Design

Use three controlled environments:

1. **Clean Healthcare IoT Lab**
   - IoT Hub configured with diagnostic settings
   - private endpoint or constrained public access where feasible
   - minimal shared access policy exposure
   - logging and monitoring configured

2. **Weak Healthcare IoT Lab**
   - public network access
   - missing diagnostics
   - broad shared access policies
   - no private endpoint
   - weak monitoring evidence

3. **Realistic Simulated Clinic Architecture**
   - IoT Hub
   - simulated device identities
   - telemetry routing to storage/Event Hub
   - Key Vault
   - Log Analytics workspace
   - public communications or remote-care component
   - explicitly labelled evidence gaps

No real patient data should be used. Simulated telemetry should use synthetic non-clinical values only.

## Expected Results

The paper should not claim complete healthcare IoT security assessment. The stronger expected result is:

> Cloud control-plane telemetry can support a meaningful subset of healthcare IoT assurance claims, especially around device identity governance, cloud ingestion exposure, logging, monitoring, retention, and shared-responsibility evidence. CRIS-IoMT makes both the supported claims and the unsupported clinical/device evidence gaps explicit.

## Paper Structure

1. Introduction
2. Background: healthcare IoT, cloud-connected IoMT, NHS assurance, and CRIS-SME
3. Threat model and assurance scope
4. CRIS-IoMT architecture
5. IoMT cloud evidence model
6. Deterministic IoMT controls
7. NHS DSPT and NCSC CAF mapping
8. Controlled Azure healthcare IoT lab design
9. Results
10. Discussion
11. Threats to validity
12. Limitations
13. Future work
14. Conclusion

## Target Venues

Best fit:

- IEEE Journal of Biomedical and Health Informatics
- IEEE Internet of Things Journal
- IEEE Sensors Journal
- Computers & Security

Workshop or conference stepping stones:

- IEEE Sensors conference track
- IEEE HealthCom
- EuroS&P workshop
- NCSC-adjacent or UK healthcare cyber venues

## Collaboration Fit

This track is a natural collaboration point with expertise in sensing, healthcare systems, communication, biomedical technologies, and cyber-physical environments.

The CRIS contribution is the deterministic cloud assurance engine. The collaborator contribution can strengthen:

- healthcare IoT threat framing
- clinical/sensing system context
- evaluation realism
- biomedical and NHS relevance
- target venue alignment
- broader cyber-physical systems discussion

