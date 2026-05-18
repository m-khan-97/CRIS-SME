# CRIS-IoMT Research Track

CRIS-IoMT is the healthcare IoT research extension of CRIS-SME.

The purpose is to study how cloud control-plane evidence can support deterministic assurance of cloud-connected healthcare IoT and Internet of Medical Things environments without inspecting patient data, clinical payloads, or device firmware.

## Core Thesis

Healthcare IoT risk is not only inside devices. It also exists in the cloud services that authenticate devices, route telemetry, store signals, expose management surfaces, monitor anomalies, and retain investigation evidence.

CRIS-IoMT extends CRIS-SME by converting healthcare IoT cloud evidence into traceable assurance findings mapped to NHS DSPT, NCSC CAF, and healthcare safety boundaries.

## Recommended Reading Order

1. `paper-plan.md`  
   Research thesis, contribution, research questions, paper structure, and venue positioning.

2. `control-model.md`  
   Proposed IoMT control catalogue, evidence inputs, scoring boundaries, and assurance mapping.

3. `evaluation-protocol.md`  
   Controlled lab design, datasets, metrics, reviewer workflow, and threats to validity.

4. `collaboration-brief.md`  
   Short professional brief for discussing the track with a senior collaborator in sensing, healthcare, and cyber-physical systems.

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

