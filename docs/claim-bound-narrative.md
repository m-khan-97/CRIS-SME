# Claim-Bound Narrative

The Claim-Bound Narrative turns verified and caveated claims into stakeholder-readable prose.

It is deterministic.

It does not call an AI provider.

It only uses claims from:

`claim_verification_pack.claims`

## Guardrails

- verified claims may be stated plainly
- caveated claims must include caveat language
- unverified claims must be described as not verified
- every section cites claim IDs
- no new claims are invented
- deterministic CRIS-SME scores are unchanged

## Report Output

CRIS-SME writes:

- `outputs/reports/cris_sme_claim_bound_narrative.json`
- `outputs/reports/cris_sme_claim_bound_narrative.md`

Reports include:

`claim_bound_narrative`

The dashboard payload includes:

`claim_bound_narrative`

The RBOM includes both narrative artifacts.

## Why This Matters

Most AI security summaries are risky because they can paraphrase beyond the evidence.

CRIS-SME's claim-bound narrative makes prose subordinate to verified claims. It is designed so a future AI narrator can only expand claim-cited material rather than inventing new conclusions.
