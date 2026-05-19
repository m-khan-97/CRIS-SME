# CRIS-IoMT Collaboration Brief

## Working Title

**CRIS-IoMT: Evidence-Driven Cloud Governance Assessment for Cloud-Connected Healthcare IoT Systems**

## Short Summary

CRIS-IoMT is a healthcare IoT research extension of CRIS. It evaluates the cloud governance layer behind cloud-connected healthcare IoT systems, including IoT Hub identity, shared access policies, public exposure, diagnostic logging, alerting, private endpoint posture, telemetry governance, and evidence boundaries.

The work is intentionally not a medical-device scanner. It does not inspect patient data, device firmware, radio protocols, or clinical telemetry payloads. Instead, it asks a narrower and practical question:

> What healthcare IoT assurance claims can be supported from cloud control-plane evidence, and which claims still require device, sensing, endpoint, clinical, or human operational evidence?

## Why This Is Interesting

Healthcare IoT research often focuses on devices, sensing, communications, biomedical instrumentation, anomaly detection, or firmware. Those layers matter, but modern healthcare IoT deployments also rely on cloud services for identity, ingestion, telemetry routing, logs, keys, monitoring, and incident evidence.

CRIS-IoMT focuses on that under-examined cloud governance layer.

## Current Evidence Base

The current implementation has:

- Azure IoT Hub live evidence collection
- ten deterministic `IOT-*` controls
- NHS DSPT and NCSC CAF-oriented mapping
- candidate NHS DSPT 2025-26 CAF-aligned outcome mappings marked for expert review
- live Azure controlled lab scenarios
- scenario-scoped evidence collection
- IoMT JSON and Markdown evidence pack exports
- deterministic scoring that preserves explainability

Live controlled runs completed:

| Scenario | Run ID | IoMT findings | Healthcare IoT score | Key observation |
| --- | --- | ---: | ---: | --- |
| Weak IoMT baseline | `20260519070105` | `10` | `26.64` | Missing diagnostics, no alerting, public IoT Hub, overbroad shared access policies. |
| Simulated clinic | `20260519105038` | `9` | `27.32` | Diagnostics and alerting observed, but public exposure, private endpoint, Defender, shared-access, and clinical-boundary gaps remain. |

The clearest controlled signal is `IOT-009`: the weak baseline had no IoT alert rule and triggered the finding; the simulated clinic deployed a real Azure Monitor IoT metric alert and did not trigger the finding. This is the result to foreground when discussing empirical validity.

## Collaboration Value

A collaborator with expertise in sensing, healthcare systems, communications, biomedical engineering, and cyber-physical systems would strengthen:

- healthcare IoT threat framing
- realism of simulated clinical architecture
- distinction between cloud-side evidence and device/sensing evidence
- NHS/clinical-operational assurance language
- review of the candidate DSPT outcome mappings, especially `B2.a`, `C1.a`, and `D1.a`
- evaluation design and reviewer credibility
- venue selection for healthcare, sensors, and cyber-physical systems audiences

## Proposed Contribution Split

CRIS contributes:

- deterministic cloud evidence engine
- Azure live collector
- IoMT control model
- reporting and evidence-pack pipeline
- controlled Azure lab harness

The collaborator can contribute:

- healthcare IoT domain framing
- sensing and device-layer boundary analysis
- clinical realism review
- paper refinement
- target venue strategy
- external academic credibility

## Best Next Discussion Questions

1. Is cloud-control-plane assurance a meaningful and under-addressed layer in healthcare IoT security?
2. Which clinical IoT failure modes should the simulated clinic architecture model?
3. Which findings are meaningful to NHS/healthcare stakeholders, and which should be reframed?
4. How should the paper describe the boundary between cloud evidence, device evidence, and clinical safety evidence?
5. Which venue is most appropriate: IEEE JBHI, IEEE IoT Journal, IEEE Sensors, HealthCom, or Computers & Security?
