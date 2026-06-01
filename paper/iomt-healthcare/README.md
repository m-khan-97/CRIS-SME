# CRIS-IoMT Paper Package

This package contains the working paper materials for:

**CRIS-IoMT: Evidence-Driven Cloud Governance Assessment for Cloud-Connected Healthcare IoT Systems**

Recommended reading order:

1. `collaboration-brief.md`
2. `related-work.md`
3. `methodology.md`
4. `threat-model.md`
5. `evaluation-results.md`
6. `main.md`

For external domain review, use `expert-review-pack/README.md` as the entry point. That folder contains the cover brief, paper summary, control matrix, evidence boundary note, evaluation summary, related-work comparison, review ledger, and suggested review request message.

The package is based on live Azure IoT Hub evidence runs recorded in `docs/research/cris-iomt/live-run-register.md`.

Generated CRIS reports and IoMT evidence packs are stored under `outputs/` and are not committed by default because live resource identifiers may appear in those artifacts.

The paper evaluation suite can be reproduced with:

```bash
CRIS_SME_IOMT_IOTHUB_SKU=B1 \
python3 scripts/azure_evidence_lab.py paper-iomt-suite \
  --location uaenorth \
  --yes
```

The suite creates the weak baseline, simulated clinic, and hardened clinic scenarios, runs CRIS-IoMT against each resource group, generates IoMT evidence packs automatically, writes a suite-level summary, and deletes the lab resources unless `--keep` is supplied.

For a stronger `IOT-006` private endpoint experiment, set `CRIS_SME_IOMT_ENABLE_PRIVATE_ENDPOINT=true` before running the suite. This path is optional because IoT Hub private endpoint support can depend on subscription, SKU, and regional availability.

Paper-grade caveats to preserve:

- NHS DSPT references are candidate 2025-26 CAF-aligned outcome mappings for expert review, not compliance assertions.
- `IOT-004` records that Defender for IoT or equivalent monitoring evidence was not observable in the assessed Azure context; it is not proof that compensating monitoring is absent.
- The `IOT` category has a base CRIS weight of `0.0` and is reported as a standalone Healthcare IoT metric.
- The key controlled empirical result now spans `IOT-005`, `IOT-007`, and `IOT-009`: the hardened clinic passed these controls after public IoT Hub access was disabled, telemetry storage routing was added, and a real Azure Monitor alert rule was deployed.
- `IOT-006` is conditional after expert review: private endpoint absence is only a finding when public ingestion is enabled and no compensating IP-filter or certificate-authority evidence is observed. Regenerate the paper suite before final submission so tables reflect this revision.
- The related-work claim should remain careful: CRIS-IoMT is positioned as an open, deterministic, evidence-sufficiency-aware research artifact for healthcare IoT cloud governance, not as a replacement for Defender for IoT, Defender for Cloud, CNAPP/CSPM, OT visibility, DSPT, or CAF.
