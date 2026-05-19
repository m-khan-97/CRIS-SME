# CRIS-IoMT Research Track

CRIS-IoMT is the healthcare IoT research extension of CRIS-SME.

The purpose is to study how cloud control-plane evidence can support deterministic assurance of cloud-connected healthcare IoT and Internet of Medical Things environments without inspecting patient data, clinical payloads, or device firmware.

## Core Thesis

Healthcare IoT risk is not only inside devices. It also exists in the cloud services that authenticate devices, route telemetry, store signals, expose management surfaces, monitor anomalies, and retain investigation evidence.

CRIS-IoMT extends CRIS-SME by converting healthcare IoT cloud evidence into traceable assurance findings mapped to candidate NHS DSPT 2025-26 CAF-aligned outcomes, NCSC CAF objectives, and healthcare safety boundaries.

## Recommended Reading Order

1. `paper-plan.md`  
   Research thesis, contribution, research questions, paper structure, and venue positioning.

2. `control-model.md`  
   Proposed IoMT control catalogue, evidence inputs, scoring boundaries, and assurance mapping.

3. `evaluation-protocol.md`  
   Controlled lab design, datasets, metrics, reviewer workflow, and threats to validity.

4. `collaboration-brief.md`  
   Short professional brief for discussing the track with a senior collaborator in sensing, healthcare, and cyber-physical systems.

5. `live-run-register.md`  
   Traceable register of live Azure IoMT runs, region policy context, generated reports, evidence packs, and cleanup state.

6. `../../../paper/iomt-healthcare/`  
   Paper-facing package containing the draft manuscript skeleton, methodology, evaluation results, and collaboration brief.

## Non-Goals

- CRIS-IoMT does not certify NHS DSPT, CAF, CE, medical-device safety, or clinical safety case compliance.
- It does not inspect patient data or clinical telemetry payloads.
- It does not test device firmware, radio protocols, or physical sensors.
- It does not replace penetration testing, clinical safety review, or biomedical engineering validation.

## First Implementation Milestone

The first implementation milestone should add:

- Azure IoT Hub inventory evidence
- IoT Hub public network and private endpoint posture
- diagnostic-settings coverage for IoT Hub telemetry
- shared access policy and device identity evidence
- Defender/security monitoring observability where available
- 10 deterministic `IOT-*` controls
- NHS DSPT and NCSC CAF mapping
- controlled healthcare IoT Azure lab scenario

## Current Live Evidence Status

The first live Azure IoMT evaluation runs have been completed in `uaenorth`:

- `20260519070105` weak IoMT baseline
- `20260519105038` simulated clinic

Both runs were assessed with resource-group scope and cleaned up by the lab cycle command. See `live-run-register.md` for artifact paths and headline results.

The key controlled result is `IOT-009`: the weak baseline had no IoT alert rule and triggered the finding, while the simulated clinic deployed a real Azure Monitor metric alert and did not trigger the finding. `IOT-004` should be treated differently: Defender for IoT was not observable in the Azure for Students evaluation environment, so that finding records a monitoring-evidence gap rather than proof that no compensating monitoring exists.
