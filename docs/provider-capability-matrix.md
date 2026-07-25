# Provider Capability Matrix

This matrix reflects **actual implementation status**, not aspirational parity.

| Capability | Azure | AWS | GCP |
| --- | --- | --- | --- |
| Adapter class present | Yes | Yes | Yes (placeholder) |
| Adapter registered for active runs | Yes | Yes | No |
| Mock profile normalization path | Yes | Yes | Not active |
| Live collector path | Yes (active) | Yes (research preview, not yet verified live) | No |
| Control evaluation support in core engine | Yes (provider-neutral core) | Yes (provider-neutral core) | Core ready, provider path not active |
| Compliance mapping | Yes | Yes | Provider-neutral mapping model, no active collector |
| Dashboard/report integration | Yes | Yes | Follows core schema when activated |
| Provider contract conformance | Active-ready | Partial (adapter + tests + docs present; live collector unverified) | Planned-ready |

## Notes

- CRIS-SME is Azure-first by active runtime support; AWS has a research-preview boto3 collector (`src/cris_sme/collectors/aws_collector.py`) covering IAM, Network, Data, Monitoring, Compute, Governance, and IoT.
- The AWS collector has been unit-tested against fake boto3 clients (`tests/test_aws_collector.py`) but has not yet been verified against a real AWS account — it must not be marked `active` until that verification happens.
- Several AWS fields are best-effort analogs of Azure concepts with no exact AWS equivalent (e.g. "Key Vault" posture approximated from KMS/Secrets Manager, "IoT Hub" posture approximated from AWS IoT Core Thing Groups). See `docs/aws-least-privilege-setup.md` for the full list of known limitations.
- GCP remains planned/placeholder to avoid overclaiming.
- Provider support should only be upgraded in this matrix after collector + tests + docs are in place, and for `active` status, after a verified live run.
- Provider Evidence Contracts now make this explicit per control and per provider in report output.
- Provider Contract Conformance makes these support claims executable in tests and report artifacts.
