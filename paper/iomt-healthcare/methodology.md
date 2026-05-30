# CRIS-IoMT Methodology

## Research Aim

CRIS-IoMT studies whether cloud control-plane evidence can support deterministic assurance decisions for cloud-connected healthcare IoT and Internet of Medical Things environments.

The method deliberately avoids patient data, clinical telemetry payload inspection, firmware analysis, wireless protocol testing, and medical-device certification claims.

## Evidence Sources

The Azure-first implementation collects evidence from:

- Azure IoT Hub inventory
- IoT Hub public network access
- IoT Hub private endpoint posture
- IoT Hub shared access policy inventory
- IoT Hub device identity inventory
- IoT Hub diagnostic settings
- Azure Monitor metric alert rules
- Microsoft Defender / security monitoring observability where available
- linked cloud governance evidence from storage, Key Vault, monitoring, and resource inventory

## Deterministic Controls

CRIS-IoMT evaluates ten deterministic controls:

| Control | Assurance question |
| --- | --- |
| `IOT-001` | Are IoMT device identities governed with strong authentication evidence? |
| `IOT-002` | Are IoT shared access policies constrained to least privilege? |
| `IOT-003` | Is IoT diagnostic logging sufficient for investigation? |
| `IOT-004` | Is Defender for IoT or equivalent security monitoring evidenced? |
| `IOT-005` | Is public IoT Hub exposure constrained? |
| `IOT-006` | Are sensitive IoMT telemetry paths covered by private endpoints where required? |
| `IOT-007` | Are telemetry routing and retention governed? |
| `IOT-008` | Are IoT credentials linked to managed secret governance? |
| `IOT-009` | Is clinical IoT alert routing operationally evidenced? |
| `IOT-010` | Are clinical-operational ownership boundaries documented for human validation? |

Each control emits a finding only when deterministic evidence indicates a weakness or when the evidence boundary itself is material to the assurance claim.

## Scenario Design

The evaluation uses three Azure lab modes:

- Clean standing demo baseline: a retained demo architecture used to validate live IoT Hub collection and browser demonstration.
- Weak IoMT baseline: intentionally weak IoT Hub posture with public exposure, broad shared access policies, missing diagnostics, missing alerting, and no private endpoint.
- Simulated clinic: a more realistic architecture with multiple device identities, diagnostic settings, metric alerting, storage, Key Vault, and segmented virtual network context.

The weak and simulated-clinic runs use resource-group scoped collection to isolate scenario evidence from other subscription resources.

## Evidence Sufficiency Boundary

CRIS-IoMT classifies cloud evidence separately from healthcare evidence that remains outside cloud observability:

- Direct cloud evidence: observed from Azure control-plane APIs or CLI commands.
- Inferred cloud evidence: derived from cloud inventory relationships.
- Unavailable cloud evidence: blocked by permissions, API limitations, or service-plan boundaries.
- Device/endpoint evidence required: needs device, firmware, endpoint, MDM, EDR, or biomedical engineering data.
- Clinical/operational evidence required: needs human documentation, clinical responsibility assignment, operating procedure, or safety-case review.

This distinction is central to the paper. CRIS-IoMT is not a certification engine; it is an evidence-driven assurance pre-assessment engine.

## NHS DSPT and NCSC CAF Mapping

IoMT controls are mapped to healthcare-readiness themes where cloud evidence is relevant. The mapping is treated as readiness support, not as compliance certification.

The mapping now records candidate NHS DSPT 2025-26 CAF-aligned outcome IDs for each `IOT-*` control. Examples include `B2.a` for identity verification, authentication and authorisation, `C1.a` for monitoring coverage, and `D1.a` for response planning. These IDs are deliberately marked as `candidate_pending_expert_review` in the machine-readable mapping because healthcare DSPT interpretation should be validated by domain experts before publication as an assessment crosswalk.

The paper should use language such as:

> CRIS-IoMT maps cloud-observable IoMT governance signals to NHS DSPT and NCSC CAF-aligned readiness themes, while explicitly preserving evidence gaps that require endpoint, device, clinical, or organisational validation.

## Scoring and Calibration Boundary

Healthcare IoT is treated as an optional research domain inside CRIS. The base SME risk model assigns the `IOT` category a weight of `0.0`; this prevents experimental IoMT findings from changing the standard CRIS SME overall score. The Healthcare IoT category score is reported separately as a standalone research metric.

The `IOT-*` confidence entries are provisional, not fully empirical. They use the three scenario-scoped Azure IoMT lab runs as the initial calibration source and should be expanded through expert review, production-like healthcare scenarios, and licensed Defender for IoT validation.

`IOT-004` is a special case. Defender for IoT was not observable in the Azure for Students evaluation environment. A triggered `IOT-004` finding therefore records that cloud security-monitoring evidence was unavailable or absent in the observed scope; it must not be interpreted as proof that no compensating SIEM, SOC, or clinical operations monitoring exists.

## Non-Claims

CRIS-IoMT does not claim to:

- certify NHS DSPT compliance
- certify NCSC CAF compliance
- certify clinical safety
- certify medical-device security
- inspect patient data
- inspect clinical telemetry payloads
- test device firmware
- test radio or sensing channels
- replace penetration testing, clinical safety review, or biomedical engineering validation
