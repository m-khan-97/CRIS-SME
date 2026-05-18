# CRIS-IoMT Evaluation Protocol

This protocol defines a high-quality evaluation path for CRIS-IoMT.

The goal is to produce a publishable healthcare IoT assurance paper, not simply to demonstrate that Azure IoT Hub can be queried.

## Evaluation Principles

1. Use controlled, authorised environments only.
2. Use synthetic devices and synthetic telemetry only.
3. Do not collect patient data, clinical measurements, or real device payloads.
4. Preserve deterministic outputs and evidence lineage.
5. Separate cloud evidence from device, clinical, endpoint, and operational evidence.
6. Report evidence gaps as results, not failures.

## Dataset Tracks

### Track A: Clean Healthcare IoT Lab

Purpose:

Establish the intended baseline and verify that CRIS-IoMT does not over-report weak posture when controls are configured well.

Expected architecture:

- Azure IoT Hub
- simulated device identities
- diagnostic settings enabled
- Log Analytics workspace
- constrained network access or private endpoint where feasible
- Key Vault with purge protection
- documented evidence boundaries

Expected outcome:

- fewer high-risk IoT findings
- evidence gaps still present for device-side and clinical-operational evidence
- clear pass/partial outcomes for logging and governance controls

### Track B: Weak Healthcare IoT Lab

Purpose:

Stress deterministic detection of known weak IoT cloud configurations.

Expected architecture:

- Azure IoT Hub with broad public network access
- diagnostic settings disabled
- broad shared access policies
- no private endpoint
- missing or weak monitoring
- storage destination without strong governance

Expected outcome:

- `IOT-002`, `IOT-003`, `IOT-004`, `IOT-005`, `IOT-006`, and `IOT-009` should trigger
- evidence output should explain why each finding was generated
- NHS DSPT and CAF readiness should show explicit gaps

### Track C: Realistic Simulated Clinic Architecture

Purpose:

Evaluate CRIS-IoMT on a more realistic but still controlled healthcare IoT design.

Expected architecture:

- IoT Hub
- simulated ward/device group identities
- message routing to Event Hub or Storage
- Log Analytics workspace
- Key Vault
- dashboard or monitoring artifact
- segmented network design
- one intentional-public component with documented justification

Expected outcome:

- mixed pass/fail/partial results
- evidence sufficiency report with meaningful clinical-operational boundaries
- better demonstration value for senior healthcare/sensing collaborators

## Metrics

Primary metrics:

- IoMT controls evaluated
- compliant/non-compliant/partial/not-applicable controls
- evidence class counts
- direct cloud evidence coverage
- inferred cloud evidence coverage
- unavailable cloud evidence count
- device-required evidence count
- clinical-operational evidence count
- NHS DSPT mapping coverage
- NCSC CAF outcome coverage
- high/medium/low IoMT findings

Secondary metrics:

- time to generate evidence pack
- number of manual evidence requests produced
- diagnostic logging coverage
- private endpoint coverage
- shared access policy count
- IoT Hub public network posture
- report usefulness rating from reviewer feedback

## Reviewer Workflow

Use at least two reviewer perspectives if possible:

1. Cloud/security reviewer:
   - validates whether the cloud evidence supports each technical finding
   - checks false positives and false negatives
   - reviews Azure evidence sufficiency

2. Healthcare/IoT reviewer:
   - validates whether the framing is meaningful for healthcare IoT
   - checks clinical and operational caveats
   - reviews NHS/CAF mapping relevance

Review states:

- accepted
- overridden
- needs evidence
- out of scope

Reviewer decisions must not change deterministic CRIS scores. They should be recorded as downstream assurance judgments.

## Lab Safety

Allowed:

- simulated devices
- synthetic telemetry labels
- Azure control-plane evidence
- Log Analytics test workspace
- dummy storage
- public endpoint posture only in owned lab subscriptions

Not allowed:

- patient data
- real medical device telemetry
- production NHS environments without written approval
- scanning third-party systems
- device firmware testing unless separately authorised and ethically reviewed

## Threats to Validity

Controlled Azure labs may not represent hospital-scale IoT deployments.

Azure IoT Hub evidence does not generalise automatically to AWS IoT Core, GCP IoT replacements, on-premises brokers, or vendor-managed platforms.

Cloud evidence cannot prove device firmware security, sensor correctness, radio-layer resilience, clinical safety, or operational process maturity.

Some security signals require higher Azure permissions or premium security products, creating observability bias.

Synthetic device identities and telemetry do not represent the behaviour of real medical devices.

Healthcare assurance mappings may require review by NHS, DSPT, CAF, or clinical safety specialists before being used outside research.

## Minimum Publishable Evaluation

A strong first paper should include:

- three controlled lab architectures
- at least 10 IoMT controls
- NHS DSPT and CAF mapping
- evidence sufficiency table
- one external expert review pass, ideally from healthcare IoT/sensing or cyber-physical systems expertise
- clear patient-data and clinical-safety boundary

