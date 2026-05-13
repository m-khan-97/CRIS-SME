# Cyber Essentials Revalidation Evidence Pack

Generated: 2026-05-13 22:47:16 UTC

This pack provides evidence for the 8 Cyber Essentials review-ledger rows whose original reviewer entries no longer match the current controlled-lab answer pack. It is intended for reviewer revalidation only. The values below are not independent human agreement results until the reviewer confirms them.

Source artifacts:

- Answer pack: `outputs/reports/azure_controlled_lab/cris_sme_ce_self_assessment.json`
- Risk report: `outputs/reports/azure_controlled_lab/cris_sme_report.json`
- Revalidation input: `paper/cyber-essentials/review-ledger-revalidation-required.csv`
- Revalidation CSV with evidence: `paper/cyber-essentials/review-ledger-revalidation-with-evidence.csv`

Reviewer decision options:

- `accepted`: the reviewer accepts the current CRIS-SME proposed answer for the controlled-lab evidence.
- `override`: the reviewer rejects the proposed answer and supplies a different final answer.
- `needs_evidence`: the reviewer cannot accept or override without additional evidence.

Important interpretation rule: a proposed `Yes` means CRIS-SME did not identify a linked risk for the mapped cloud controls in the current evidence pack. It is not a certification statement. A proposed `No` means CRIS-SME found linked risk evidence for the mapped controls.

## Rows Requiring Revalidation

### A2.2.2 - Explain the mechanism used to create any subset boundary.

- Current evidence class: `inferred_cloud`
- Current proposed status: `supported_risk_found`
- Current proposed answer: `No`
- Supporting controls: `NET-002`
- Human review required: `True`
- Caveat: CRIS-SME found related cloud evidence that may affect this answer. A responsible person must verify the final Cyber Essentials response.
- Answer basis: A mapped CRIS-SME risk finding is present, so the candidate CE answer is No pending human verification.

Linked findings:
- `fdg_aae1f418c95de1` / `NET-002`: Network security group rules are broader than expected (severity High, priority Planned, score 44.71). Evidence quality: observed / partial. Score factors: severity=7.0, L=1.44, D=1.28, C=0.9625, R=1.06.

Evidence statements:
- 2 permissive NSG rule(s) were identified

Reviewer action: re-confirm this row against the current controlled-lab evidence and fill `revalidated_review_state`, `revalidated_final_answer`, `revalidated_note`, and `revalidated_at` in the CSV companion file.

### A2.4 - List networks included in the assessment scope.

- Current evidence class: `inferred_cloud`
- Current proposed status: `supported_risk_found`
- Current proposed answer: `No`
- Supporting controls: `NET-002`
- Human review required: `True`
- Caveat: CRIS-SME found related cloud evidence that may affect this answer. A responsible person must verify the final Cyber Essentials response.
- Answer basis: A mapped CRIS-SME risk finding is present, so the candidate CE answer is No pending human verification.

Linked findings:
- `fdg_aae1f418c95de1` / `NET-002`: Network security group rules are broader than expected (severity High, priority Planned, score 44.71). Evidence quality: observed / partial. Score factors: severity=7.0, L=1.44, D=1.28, C=0.9625, R=1.06.

Evidence statements:
- 2 permissive NSG rule(s) were identified

Reviewer action: re-confirm this row against the current controlled-lab evidence and fill `revalidated_review_state`, `revalidated_final_answer`, `revalidated_note`, and `revalidated_at` in the CSV companion file.

### A2.5 - List in-scope routers, firewalls, or equivalent network-boundary equipment.

- Current evidence class: `inferred_cloud`
- Current proposed status: `supported_risk_found`
- Current proposed answer: `No`
- Supporting controls: `NET-002`
- Human review required: `True`
- Caveat: CRIS-SME found related cloud evidence that may affect this answer. A responsible person must verify the final Cyber Essentials response.
- Answer basis: A mapped CRIS-SME risk finding is present, so the candidate CE answer is No pending human verification.

Linked findings:
- `fdg_aae1f418c95de1` / `NET-002`: Network security group rules are broader than expected (severity High, priority Planned, score 44.71). Evidence quality: observed / partial. Score factors: severity=7.0, L=1.44, D=1.28, C=0.9625, R=1.06.

Evidence statements:
- 2 permissive NSG rule(s) were identified

Reviewer action: re-confirm this row against the current controlled-lab evidence and fill `revalidated_review_state`, `revalidated_final_answer`, `revalidated_note`, and `revalidated_at` in the CSV companion file.

### A2.5.1 - List equipment used to define any partial-scope subset.

- Current evidence class: `inferred_cloud`
- Current proposed status: `supported_risk_found`
- Current proposed answer: `No`
- Supporting controls: `NET-002`
- Human review required: `True`
- Caveat: CRIS-SME found related cloud evidence that may affect this answer. A responsible person must verify the final Cyber Essentials response.
- Answer basis: A mapped CRIS-SME risk finding is present, so the candidate CE answer is No pending human verification.

Linked findings:
- `fdg_aae1f418c95de1` / `NET-002`: Network security group rules are broader than expected (severity High, priority Planned, score 44.71). Evidence quality: observed / partial. Score factors: severity=7.0, L=1.44, D=1.28, C=0.9625, R=1.06.

Evidence statements:
- 2 permissive NSG rule(s) were identified

Reviewer action: re-confirm this row against the current controlled-lab evidence and fill `revalidated_review_state`, `revalidated_final_answer`, `revalidated_note`, and `revalidated_at` in the CSV companion file.

### A4.1 - Confirm firewall protection exists between in-scope systems and the internet.

- Current evidence class: `inferred_cloud`
- Current proposed status: `supported_risk_found`
- Current proposed answer: `No`
- Supporting controls: `NET-001`, `NET-002`
- Human review required: `True`
- Caveat: CRIS-SME found related cloud evidence that may affect this answer. A responsible person must verify the final Cyber Essentials response.
- Answer basis: A mapped CRIS-SME risk finding is present, so the candidate CE answer is No pending human verification.

Linked findings:
- `fdg_c698d41a33cfb4` / `NET-001`: Administrative services are exposed to the public internet (severity Critical, priority High, score 72.12). Evidence quality: observed / sufficient. Score factors: severity=10.0, L=1.6, D=1.28, C=0.985, R=1.0525.
- `fdg_aae1f418c95de1` / `NET-002`: Network security group rules are broader than expected (severity High, priority Planned, score 44.71). Evidence quality: observed / partial. Score factors: severity=7.0, L=1.44, D=1.28, C=0.9625, R=1.06.

Evidence statements:
- 1 asset(s) expose RDP to the public internet
- 1 asset(s) expose SSH to the public internet
- 2 permissive NSG rule(s) were identified

Reviewer action: re-confirm this row against the current controlled-lab evidence and fill `revalidated_review_state`, `revalidated_final_answer`, `revalidated_note`, and `revalidated_at` in the CSV companion file.

### A4.7 - Confirm unauthenticated inbound connections are blocked by default.

- Current evidence class: `direct_cloud`
- Current proposed status: `supported_risk_found`
- Current proposed answer: `No`
- Supporting controls: `NET-001`, `NET-002`
- Human review required: `True`
- Caveat: CRIS-SME found related cloud evidence that may affect this answer. A responsible person must verify the final Cyber Essentials response.
- Answer basis: A mapped CRIS-SME risk finding is present, so the candidate CE answer is No pending human verification.

Linked findings:
- `fdg_c698d41a33cfb4` / `NET-001`: Administrative services are exposed to the public internet (severity Critical, priority High, score 72.12). Evidence quality: observed / sufficient. Score factors: severity=10.0, L=1.6, D=1.28, C=0.985, R=1.0525.
- `fdg_aae1f418c95de1` / `NET-002`: Network security group rules are broader than expected (severity High, priority Planned, score 44.71). Evidence quality: observed / partial. Score factors: severity=7.0, L=1.44, D=1.28, C=0.9625, R=1.06.

Evidence statements:
- 1 asset(s) expose RDP to the public internet
- 1 asset(s) expose SSH to the public internet
- 2 permissive NSG rule(s) were identified

Reviewer action: re-confirm this row against the current controlled-lab evidence and fill `revalidated_review_state`, `revalidated_final_answer`, `revalidated_note`, and `revalidated_at` in the CSV companion file.

### A4.9 - Confirm whether firewall configuration interfaces are internet-accessible.

- Current evidence class: `direct_cloud`
- Current proposed status: `supported_risk_found`
- Current proposed answer: `No`
- Supporting controls: `NET-001`
- Human review required: `True`
- Caveat: CRIS-SME found related cloud evidence that may affect this answer. A responsible person must verify the final Cyber Essentials response.
- Answer basis: A mapped CRIS-SME risk finding is present, so the candidate CE answer is No pending human verification.

Linked findings:
- `fdg_c698d41a33cfb4` / `NET-001`: Administrative services are exposed to the public internet (severity Critical, priority High, score 72.12). Evidence quality: observed / sufficient. Score factors: severity=10.0, L=1.6, D=1.28, C=0.985, R=1.0525.

Evidence statements:
- 1 asset(s) expose RDP to the public internet
- 1 asset(s) expose SSH to the public internet

Reviewer action: re-confirm this row against the current controlled-lab evidence and fill `revalidated_review_state`, `revalidated_final_answer`, `revalidated_note`, and `revalidated_at` in the CSV companion file.

### A5.4 - Identify externally reachable services that provide access to non-public data.

- Current evidence class: `direct_cloud`
- Current proposed status: `supported_risk_found`
- Current proposed answer: `No`
- Supporting controls: `NET-001`, `DATA-001`
- Human review required: `True`
- Caveat: CRIS-SME found related cloud evidence that may affect this answer. A responsible person must verify the final Cyber Essentials response.
- Answer basis: A mapped CRIS-SME risk finding is present, so the candidate CE answer is No pending human verification.

Linked findings:
- `fdg_c698d41a33cfb4` / `NET-001`: Administrative services are exposed to the public internet (severity Critical, priority High, score 72.12). Evidence quality: observed / sufficient. Score factors: severity=10.0, L=1.6, D=1.28, C=0.985, R=1.0525.
- `fdg_7d248da4942588` / `DATA-001`: Public storage access increases data exposure risk (severity High, priority Planned, score 48.35). Evidence quality: observed / partial. Score factors: severity=7.0, L=1.56, D=1.28, C=0.9745, R=1.045.

Evidence statements:
- 1 asset(s) expose RDP to the public internet
- 1 asset(s) expose SSH to the public internet
- 1 storage asset(s) allow public access

Reviewer action: re-confirm this row against the current controlled-lab evidence and fill `revalidated_review_state`, `revalidated_final_answer`, `revalidated_note`, and `revalidated_at` in the CSV companion file.

