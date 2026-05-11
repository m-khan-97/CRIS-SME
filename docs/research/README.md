# Cyber Essentials Research Pack

This folder contains the paper-facing Cyber Essentials material for CRIS-SME. It is designed to be usable directly from GitHub without relying on generated local report files.

## Recommended Reading Order

1. `cyber-essentials-paper-skeleton.md`  
   Main manuscript scaffold, research questions, contribution framing, current numbers, and artifact checklist.

2. `ce-question-coverage-analysis.md`  
   The methodological argument: what can and cannot be answered from cloud control-plane telemetry.

3. `ce-question-mapping-summary.md`  
   Summary of the 106-entry paraphrased Danzell mapping and evidence-class distribution.

4. `cyber-essentials-evaluation-protocol.md`  
   How to run evaluations, conduct review, handle AI-assisted pilot ledgers, and avoid overclaiming certification.

5. `controlled-azure-lab-run-2026-05-07.md`  
   The latest controlled vulnerable-lab run, including architecture, exact CRIS-SME results, CE outputs, and cleanup statement.

6. `ce-question-annotation-matrix.md`  
   Earlier annotation matrix used to design the question-level mapping.

## Current Headline Numbers

Question-level CE mapping:

- mapped entries: `106`
- technical-control entries: `62`
- cloud-supported entries: `28` (`26.42%`)
- technical cloud-supported entries: `22` (`35.48%`)
- non-cloud evidence required: `78`

Controlled Azure vulnerable-lab run, 2026-05-07:

- overall CRIS-SME risk score: `40.16/100`
- non-compliant findings: `18`
- network score: `58.42`
- data score: `41.74`
- CE proposed answers: `23` No, `5` Yes, `78` Cannot determine
- AI-assisted pilot ledger: `23` accepted, `5` needs evidence, `78` pending

Important boundary:

The AI-assisted pilot ledger is not independent human assessor agreement. It is an internal research artifact used to validate the workflow and produce pilot metrics. A CE-knowledgeable human reviewer must validate the ledger before the paper claims expert agreement.

The `Yes` answers are also bounded. They mean CRIS-SME observed no mapped cloud-control-plane risk for the relevant controls; they do not prove that all endpoint, application-layer, SaaS, inherited-rule, or business-process aspects of the CE requirement are satisfied.

## Best Paper Title

**Evidence-Sufficiency-Aware Cyber Essentials Pre-Population From Cloud Control-Plane Telemetry**

Avoid titles that imply automated certification.
