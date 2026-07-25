# CRIS-IoMT Control Model

This document defines the first research-grade IoMT control catalogue for CRIS-IoMT.

The controls are intentionally cloud-side controls. They assess the governance and assurance posture of cloud services that support healthcare IoT environments. They do not assess medical device safety, clinical correctness, sensor accuracy, or firmware security.

## Evidence Classes

CRIS-IoMT should classify each control result using evidence sufficiency:

| Evidence Class | Meaning |
| --- | --- |
| `direct_cloud` | The Azure control plane directly exposes the evidence needed for the decision. |
| `inferred_cloud` | Cloud evidence supports the decision, but reviewer interpretation is needed. |
| `unavailable_cloud` | The signal is cloud-side but unavailable due to permissions, SKU, API limitations, or disabled service. |
| `device_required` | Device, firmware, MDM, local network, or endpoint evidence is required. |
| `clinical_operational_required` | Clinical workflow, biomedical engineering, operational safety, or organisational evidence is required. |
| `not_applicable` | The control is not applicable to the assessed architecture. |

## Proposed Controls

### IOT-001: Cloud Device-Identity Registration Posture

Assesses whether cloud-side IoT device identity registration governance is observable and whether the environment avoids weak or unauditable cloud registration posture. This control does not claim to validate device-side credential storage or firmware trust anchors.

Evidence inputs:

- IoT Hub device identity count
- authentication mechanism metadata where observable
- certificate authority configuration where available
- disabled/stale device identities where available
- evidence gap for device-side credential storage

Risk decision:

- fail when device identity inventory is unavailable or weakly governed
- partial when cloud inventory is visible but device credential assurance is not observable
- pass when device identity inventory and authentication posture are observable and constrained

Mapping:

- NHS DSPT candidate outcome: `B2.a` identity verification, authentication and authorisation
- NCSC CAF: B2 identity and access control

### IOT-002: Shared Access Policy and Key Exposure Risk

Assesses whether IoT Hub shared access policies are minimized and whether broad registry/service permissions create unnecessary blast radius.

Evidence inputs:

- IoT Hub shared access policies
- policy rights such as registry read/write, service connect, device connect
- count of custom policies
- evidence of overbroad default policy usage where observable

Risk decision:

- fail when broad shared access policies exist without compensating evidence
- partial when policies are visible but usage cannot be attributed
- pass when policies are minimized and scoped

Mapping:

- NHS DSPT candidate outcomes: `B2.a` identity verification, authentication and authorisation; `B3.a` secure configuration
- NCSC CAF: B2 identity and access control

### IOT-003: IoT Telemetry Diagnostic Logging

Assesses whether IoT Hub operational and security-relevant logs are routed to durable monitoring destinations.

Evidence inputs:

- Azure diagnostic settings for IoT Hub
- Log Analytics, Event Hub, or Storage destinations
- enabled categories and metrics
- retention evidence where observable

Risk decision:

- fail when diagnostics are absent
- partial when diagnostics are enabled but category coverage is incomplete
- pass when logs and metrics are routed to a governed destination

Mapping:

- NHS DSPT candidate outcome: `C1.a` monitoring coverage
- NCSC CAF: C1 security monitoring

### IOT-004: IoT Security Monitoring and Defender Coverage

Assesses whether cloud-side IoT threat monitoring or Defender-style security evidence is available.

Evidence inputs:

- Defender for IoT or Defender for Cloud coverage signals where accessible
- security recommendations for IoT resources
- alerting integration
- explicit unavailable evidence if tenant permissions or SKU do not expose the signal

Risk decision:

- fail when monitoring is absent for IoT resources
- partial when monitoring cannot be observed
- pass when IoT security monitoring is enabled and evidence is traceable

Mapping:

- NHS DSPT candidate outcomes: `C1.a` monitoring coverage; `C2.a` proactive security event discovery
- NCSC CAF: C1 security monitoring, C2 proactive security event discovery

Note: in the Azure for Students lab environment, Defender for IoT was not observable. A triggered `IOT-004` finding should be read as a monitoring-evidence gap, not proof that no compensating SIEM, SOC, or clinical operations monitoring exists.

### IOT-005: Public Network Exposure of IoT Ingestion Endpoints

Assesses whether IoT ingestion and management endpoints are exposed more broadly than intended.

Evidence inputs:

- IoT Hub public network access
- firewall rules and allowed IP ranges
- private endpoint connections
- public endpoint usage caveat

Risk decision:

- fail when public network access is unrestricted and no intentional-public justification exists
- partial when public access is required but compensating controls are not evidenced
- pass when private endpoint or constrained access is used

Mapping:

- NHS DSPT candidate outcome: `B4.a` secure by design
- NCSC CAF: B4 data security, B5 resilient networks and systems

### IOT-006: Conditional Private Endpoint and Network Isolation Posture

Assesses whether sensitive healthcare IoT services have uncompensated public ingestion when private connectivity is absent. Private endpoint absence is only treated as a finding when public network access is enabled and CRIS-IoMT does not observe compensating IP-filter or certificate-authority evidence.

Evidence inputs:

- private endpoint count and connection state
- VNet/subnet association
- firewall/default action
- public network access state
- IP filter evidence
- certificate-authority evidence
- intentional-public exception metadata

Risk decision:

- fail when sensitive IoT services lack private endpoint evidence and public ingestion is not compensated by observed IP filters or certificate-authority evidence
- partial when public exposure is intentional but not documented
- pass when isolation is configured, public access is disabled, or compensating cloud-side boundary evidence is observed

Mapping:

- NHS DSPT candidate outcomes: `B4.a` secure by design; `B5.a` resilient networks and systems
- NCSC CAF: B5 resilient networks and systems

### IOT-007: Telemetry Storage and Retention Governance

Assesses whether IoT telemetry routing, storage, and retention are governed for investigation, privacy, and operational continuity.

Evidence inputs:

- message routing destinations
- storage account posture
- data retention settings where observable
- lifecycle management policies
- backup/retention controls already collected by CRIS-SME

Risk decision:

- fail when telemetry destinations are ungoverned or retention is not evidenced
- partial when destination exists but retention/privacy posture is incomplete
- pass when routing and retention are governed

Mapping:

- NHS DSPT candidate outcome: `B4.b` secure data management
- NCSC CAF: B4 data security, D1 response and recovery planning

### IOT-008: Key Vault and Secret Management for IoT Integrations

Assesses whether secrets used by IoT integrations are protected with strong key-management posture.

Evidence inputs:

- Key Vault inventory
- purge protection
- private endpoint where applicable
- secret/key rotation evidence where available
- link to existing CRIS DATA-004 evidence

Risk decision:

- fail when IoT-adjacent secrets are not protected by Key Vault or equivalent evidence
- partial when Key Vault exists but rotation or access boundaries are unavailable
- pass when key-management posture is strong and linked to IoT integrations

Mapping:

- NHS DSPT candidate outcomes: `B2.a` identity verification, authentication and authorisation; `B4.b` secure data management
- NCSC CAF: B3 data security, B2 identity and access control

### IOT-009: Incident Detection and Alerting Coverage

Assesses whether IoT-related telemetry, logs, and alerts can support incident response.

Evidence inputs:

- Azure Monitor alert rules
- Log Analytics workspace
- diagnostic settings
- security alert integrations
- action groups where observable

Risk decision:

- fail when IoT telemetry exists without alerting or investigation path
- partial when logs exist but alerting is absent
- pass when logs, alerts, and response routing are evidenced

Mapping:

- NHS DSPT candidate outcomes: `C1.a` monitoring coverage; `D1.a` response plan
- NCSC CAF: C1 security monitoring, D2 lessons learned

### IOT-010: Evidence Sufficiency and Clinical Safety Boundary

Assesses whether the assessment clearly distinguishes cloud evidence from device, clinical, and operational evidence.

Evidence inputs:

- evidence class counts
- unavailable evidence count
- device-required evidence paths
- clinical/operational confirmation paths
- report caveats

Risk decision:

- fail when IoMT claims are made without evidence-class boundaries
- partial when evidence gaps are recorded but not operationally assigned
- pass when cloud evidence, device evidence, and clinical evidence boundaries are explicit

Mapping:

- NHS DSPT candidate outcomes: `A2.a` risk management process; `D1.a` response plan
- NCSC CAF: A1 governance, A2 risk management

## Scoring Guidance

IoMT controls should use the existing CRIS scoring model but adjust modifiers carefully:

- data sensitivity should default to healthcare-level sensitivity
- confidence should be reduced when evidence is inferred or unavailable
- remediation effort should reflect operational disruption in healthcare settings
- lifecycle status should distinguish lab evidence from production evidence

No IoMT control should imply clinical safety approval. Clinical and biomedical assurance remains outside deterministic cloud scoring.

Healthcare IoT is an optional research category in the base CRIS scoring model. The `IOT` category currently has a weight of `0.0`, so IoMT findings are reported in a standalone Healthcare IoT category score without changing the standard SME overall risk score. This keeps the experimental IoMT extension visible without contaminating the original SME risk model.

Determinism applies to the normalized evidence-to-finding and finding-to-score steps. The cloud environment-to-evidence collection step still depends on Azure permissions, regional feature support, SKU availability, service eventual consistency, and whether optional services such as Defender for IoT are licensed and observable.
