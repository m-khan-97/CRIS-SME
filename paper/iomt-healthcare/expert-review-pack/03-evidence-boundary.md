# Evidence Boundary

CRIS-IoMT is deliberately scoped to the cloud governance layer behind healthcare IoT deployments. Its value is not that it certifies healthcare IoT security. Its value is that it makes cloud-observable evidence and non-observable evidence explicit.

## Cloud Evidence CRIS-IoMT Can Assess

CRIS-IoMT can assess cloud-side signals such as:

- Azure IoT Hub inventory
- IoT Hub device identity inventory where observable
- IoT Hub shared access policies and policy rights
- IoT Hub public network access state
- allowed IP rules and private endpoint posture
- diagnostic settings and logging destinations
- Azure Monitor alert rules and action groups
- IoT message routing and telemetry storage destinations
- Key Vault linkage and secret-governance signals where observable
- evidence classes, unavailable signals, and report caveats

## Evidence CRIS-IoMT Cannot Assess

CRIS-IoMT cannot assess:

- clinical safety
- NHS DSPT certification
- NCSC CAF certification
- medical-device certification
- physiological sensing correctness
- device firmware integrity
- wireless or radio-channel security
- physical tampering
- endpoint/MDM compliance unless integrated separately
- patient-data content
- clinical telemetry payload semantics
- biomedical engineering acceptance
- supplier contractual controls
- clinical incident response quality

## Why This Boundary Matters

Without an explicit boundary, cloud governance tools can be misread as certifying device security or clinical safety. CRIS-IoMT avoids that by treating several controls as evidence-sufficiency controls, not just pass/fail technical checks.

For example:

- `IOT-004` records whether Defender for IoT or equivalent monitoring evidence is observable. If it is not observable, this is an evidence gap, not proof that no compensating monitoring exists.
- `IOT-010` explicitly records that clinical-operational ownership, safety-case evidence, biomedical engineering validation, and operational acceptance require human review.
- `IOT-006` treats private endpoint absence as a risk only when public ingestion is enabled and CRIS-IoMT does not observe compensating IP-filter or certificate-authority evidence; accepted public managed-ingestion designs still require expert review.

This makes the paper's claim defensible: CRIS-IoMT provides evidence-informed pre-assessment of healthcare IoT cloud governance, not certification of the entire healthcare IoT system.
