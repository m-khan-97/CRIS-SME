# Related Work Comparison

CRIS-IoMT is positioned as a narrow, open, deterministic research artifact for healthcare IoT cloud governance. It does not replace commercial CSPM, OT visibility, IoT monitoring, or assurance frameworks.

| System or framework | Primary scope | Live cloud evidence collection | Explicit evidence boundary | UK healthcare assurance orientation | Open artifact |
| --- | --- | ---: | ---: | ---: | ---: |
| CRIS-IoMT | Healthcare IoT cloud governance | Yes | Yes | Candidate DSPT/CAF evidence | Yes |
| Microsoft Defender for IoT | IoT/OT monitoring and detection | Partial | Product-dependent | Not primary framing | No |
| Microsoft Defender for Cloud | CSPM and cloud compliance | Yes | Product-dependent | Broad compliance | No |
| AWS IoT Device Defender | AWS IoT fleet auditing and monitoring | AWS-only | Product-dependent | No NHS-specific base mapping | No |
| Wiz / Prisma-style CSPM | Cloud risk prioritisation and compliance | Yes | Product-dependent | Broad compliance | No |
| Cisco Cyber Vision-style OT visibility | Industrial and OT network visibility | Network/device layer | Product-dependent | Not cloud-governance specific | No |
| IEC 80001 / NIST CSF / NHS DSPT / NCSC CAF | Risk management and assurance guidance | No | Guidance-driven | Native or adjacent assurance target | Public guidance, not live evidence tooling |
| Academic IoMT security frameworks | Device, firmware, wireless, sensing, privacy, ML, anomaly detection | Usually no | Usually implicit | Rarely mapped to DSPT/CAF | Varies |

## Bounded Novelty Claim

Our review of official product and framework materials did not identify an open, reproducible artifact that combines:

1. healthcare IoT cloud-governance scope
2. deterministic evidence-to-control decisions
3. explicit evidence-sufficiency boundaries
4. candidate NHS DSPT 2025-26 CAF-aligned and NCSC CAF-oriented mappings

This is the novelty claim the paper should preserve. The claim is not that CRIS-IoMT is broader or more capable than commercial platforms. The claim is that it exposes a specific research-grade evidence boundary for healthcare IoT cloud governance.
