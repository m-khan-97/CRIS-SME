# CRIS-IoMT Paper Package

This package contains the working paper materials for:

**CRIS-IoMT: Evidence-Driven Cloud Governance Assessment for Cloud-Connected Healthcare IoT Systems**

Recommended reading order:

1. `collaboration-brief.md`
2. `methodology.md`
3. `threat-model.md`
4. `evaluation-results.md`
5. `main.md`

The package is based on live Azure IoT Hub evidence runs recorded in `docs/research/cris-iomt/live-run-register.md`.

Generated CRIS reports and IoMT evidence packs are stored under `outputs/` and are not committed by default because live resource identifiers may appear in those artifacts.

Paper-grade caveats to preserve:

- NHS DSPT references are candidate 2025-26 CAF-aligned outcome mappings for expert review, not compliance assertions.
- `IOT-004` records that Defender for IoT or equivalent monitoring evidence was not observable in the assessed Azure context; it is not proof that compensating monitoring is absent.
- The `IOT` category has a base CRIS weight of `0.0` and is reported as a standalone Healthcare IoT metric.
- The key controlled empirical result is `IOT-009`: the simulated clinic passed only after a real Azure Monitor alert rule was deployed.
