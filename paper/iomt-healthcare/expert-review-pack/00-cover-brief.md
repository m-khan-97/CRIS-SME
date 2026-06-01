# CRIS-IoMT Expert Review Brief

## What CRIS-IoMT Is

CRIS-IoMT is an evidence-driven cloud governance assessment prototype for cloud-connected healthcare IoT and Internet of Medical Things environments.

It extends CRIS by collecting Azure IoT Hub and related cloud control-plane evidence, then converting that evidence into deterministic, traceable healthcare IoT governance findings. The system evaluates cloud-side signals such as IoT Hub identity posture, shared access policies, diagnostic logging, alerting, public network exposure, private endpoint posture, telemetry routing, secret governance, and clinical-operational evidence boundaries.

## What It Is Not

CRIS-IoMT is not a medical-device scanner, clinical safety case, DSPT certification engine, CAF certification engine, or OT network sensor. It does not inspect patient data, clinical telemetry payloads, device firmware, radio channels, physiological sensing correctness, or medical-device safety.

The central research question is narrower:

> Which healthcare IoT assurance claims can be supported from cloud control-plane evidence, and which claims still require device, endpoint, sensing, clinical, or human operational evidence?

## Why Expert Review Is Requested

The system now has a working Azure-first collector, ten deterministic `IOT-*` controls, controlled Azure lab scenarios, JSON/Markdown evidence packs, candidate NHS DSPT 2025-26 CAF-aligned mappings, and NCSC CAF-oriented readiness themes.

We are seeking expert review before presenting the paper as a mature healthcare IoT research contribution.

## Review Questions

1. Are the proposed `IOT-*` controls meaningful healthcare IoT assurance signals?
2. Are the cloud evidence boundaries scientifically and clinically defensible?
3. Are the candidate NHS DSPT / NCSC CAF mappings credible, or do they need revision?
4. Which additions would make the work stronger for IEEE JBHI, IEEE Sensors, IEEE IoT Journal, HealthCom, or a healthcare cyber venue?

