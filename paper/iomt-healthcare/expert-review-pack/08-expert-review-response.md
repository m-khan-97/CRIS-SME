# Expert Review Response

This note records how the first expert-review feedback was incorporated into CRIS-IoMT. It is intended as an internal traceability artifact for the paper package, not as a formal peer-review rebuttal.

## Accepted Revisions

- `IOT-001` was renamed and narrowed to **Cloud device-identity registration posture**. The control now explicitly covers cloud-side IoT Hub registration and authentication metadata, not device-side credential storage, firmware trust anchors, or clinical device ownership.
- The `IOT-001` NHS DSPT candidate mapping was narrowed to `B2.a`. The previous `B4.d` candidate was removed because cloud device registration evidence alone is not enough to support a vulnerability-management claim.
- `IOT-005` was narrowed to `B4.a`. The previous `C1.a` candidate was removed because public ingestion exposure is a secure-design/network-boundary signal, not monitoring coverage.
- `IOT-006` was reframed as a conditional private-endpoint control. Private endpoint absence is now a finding only when public ingestion is enabled and CRIS-IoMT does not observe compensating IP-filter or certificate-authority evidence.
- `IOT-007` was narrowed to `B4.b`. The previous `E3.a` candidate was removed because cloud telemetry routing evidence does not prove lawful direct-care information use.
- The paper now explains the simulated-clinic score inversion: the simulated clinic has fewer findings than the weak baseline but a slightly higher Healthcare IoT category score because remaining findings carry different deterministic severity, confidence, exposure, and remediation factors.
- The paper now states that determinism applies to normalized evidence-to-finding and finding-to-score decisions. Azure evidence collection itself may vary with permissions, SKU, region, API visibility, and service eventual consistency.
- The related-work comparison now uses factual axes instead of subjective product ratings and includes IEC 80001 and NIST CSF as adjacent healthcare/critical-system risk-management frameworks.
- `IOT-004` is framed as an observability-gap design demonstration when Defender for IoT or equivalent monitoring evidence is unavailable, not as proof that compensating monitoring is absent.

## Remaining Pre-Submission Actions

- Regenerate the controlled Azure IoMT suite with the revised `IOT-006` semantics so final scenario counts and Healthcare IoT scores match the reviewed control model.
- Ask a healthcare IoT/domain expert to review the narrowed DSPT/CAF candidate mappings, especially `B2.a`, `B4.a`, `B4.b`, `C1.a`, and `D1.a` claims.
- If possible, run a licensed environment where Defender for IoT is observable so `IOT-004` can be evaluated as a discriminating monitoring signal rather than only an observability boundary.
- Add device-side or endpoint/MDM evidence in a later extension if the paper scope expands beyond cloud governance.

## Paper Wording Rule

Use this phrasing consistently:

> CRIS-IoMT contributes candidate cloud evidence toward healthcare IoT assurance review. It does not certify NHS DSPT, NCSC CAF, medical-device security, clinical safety, or end-to-end IoMT security.
