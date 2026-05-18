# CRIS-IoMT Collaboration Brief

## Project Summary

CRIS-IoMT is a proposed research extension of CRIS-SME focused on cloud-connected healthcare IoT and Internet of Medical Things assurance.

The premise is that healthcare IoT security is not limited to devices, sensors, and communication channels. Modern deployments also rely on cloud services for device identity, telemetry ingestion, logging, monitoring, storage, and incident investigation. Weak cloud governance in these services can create healthcare IoT risk even when the sensing or device layer is well engineered.

CRIS-IoMT converts cloud control-plane evidence into deterministic, explainable assurance findings for healthcare IoT environments.

## Why This Is Distinctive

The work is not another vulnerability scanner and not a clinical device-certification tool.

The distinctive contribution is an evidence-sufficiency-aware method for healthcare IoT cloud assurance:

- what the cloud control plane can directly evidence
- what can only be inferred
- what is unavailable due to permissions or service limits
- what requires device, firmware, endpoint, or clinical-operational evidence
- what must remain a human assurance judgment

## Collaboration Fit

A senior collaborator with expertise in sensing, healthcare technologies, communications, and cyber-physical systems can strengthen:

- healthcare IoT threat framing
- realism of the simulated clinical architectures
- distinction between cloud evidence and device/sensing evidence
- NHS and clinical-operational relevance
- biomedical and cyber-physical systems discussion
- target journal positioning

CRIS contributes the deterministic cloud evidence engine, reporting pipeline, and evaluation harness. The collaboration contributes domain depth and research framing for healthcare IoT systems.

## Proposed Paper

Working title:

**CRIS-IoMT: Evidence-Driven Cloud Governance Assessment for Cloud-Connected Healthcare IoT Systems**

Core claim:

> Cloud-side control-plane telemetry can support a meaningful subset of healthcare IoT assurance claims, especially around device identity governance, ingestion exposure, logging, monitoring, key management, and incident evidence retention. CRIS-IoMT makes both supported claims and unsupported clinical/device evidence gaps explicit.

## Proposed Evaluation

Three controlled Azure labs:

1. clean healthcare IoT baseline
2. intentionally weak healthcare IoT lab
3. realistic simulated clinic architecture

No patient data or real medical telemetry is used.

Metrics:

- evidence coverage
- IoMT controls triggered
- evidence gaps by class
- NHS DSPT and NCSC CAF mapping coverage
- reviewer assessment of report usefulness and correctness

## What Would Be Asked From The Collaborator

Potential collaboration activities:

- review the paper framing
- advise on healthcare IoT architecture realism
- review the proposed IoMT controls
- validate clinical/sensing boundary language
- co-design the evaluation protocol
- support target venue selection
- contribute to paper writing and related work

The collaboration should be framed as a research contribution, not as endorsement of a product.

## First Discussion Questions

1. Is the cloud-control-plane assurance framing meaningful for healthcare IoT and sensing systems?
2. Which healthcare IoT cloud failure modes would be most important to model?
3. Which NHS/healthcare assurance mappings are credible and which should be avoided?
4. What would make the controlled lab realistic enough for a strong paper?
5. Which venue would best fit a cloud-governance plus healthcare-IoT assurance contribution?

