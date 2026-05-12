# Cyber Essentials Evaluation Protocol

This protocol defines how to evaluate the CRIS-SME Cyber Essentials workflow without overclaiming certification automation.

## Evaluation Boundary

CRIS-SME is evaluated as a pre-population and evidence support system.

It must not be described as:

- a Cyber Essentials certifier
- an automated certification submission system
- a replacement for a human applicant or assessor

It may be described as:

- a deterministic evidence-preparation tool
- a question-level pre-population workflow
- an evidence sufficiency classifier
- a human-review ledger for Cyber Essentials preparation

## Required Inputs

For each evaluation tenant or lab:

1. CRIS-SME report JSON.
2. CE self-assessment answer pack.
3. CE review console ledger.
4. CE evaluation metrics pack.
5. CE paper tables export.
6. Authorization statement for live environments.

Required generated files:

- `cris_sme_report.json`
- `cris_sme_ce_self_assessment.json`
- `cris_sme_ce_review_console.json`
- `cris_sme_ce_evaluation_metrics.json`
- `cris_sme_ce_paper_tables.md`
- `cris_sme_ce_chart_data.json`

## Dataset Classes

### Synthetic Baseline

Purpose:
Exercise all deterministic reporting paths with stable mock evidence.

Minimum acceptance:

- pipeline completes
- CE answer pack generated
- review console generated
- metrics generated
- paper tables generated

### Controlled Live Azure Subscription

Purpose:
Validate that the CE workflow operates on live Azure control-plane evidence.

Minimum acceptance:

- authenticated Azure collector run completes
- collector mode is `azure`
- generated report includes CE artifacts
- evidence sufficiency boundaries are visible
- no unauthorized resources are accessed

### Vulnerable Lab

Purpose:
Stress known evidence paths with intentionally weak posture.

Minimum acceptance:

- lab is owned or explicitly authorized
- lab evidence is labelled as vulnerable lab
- findings are not generalized as normal SME posture
- resources are removed after validation if they incur cost or exposure

### Real SME Tenant

Purpose:
Measure reviewer agreement and practical evidence retrieval value.

Minimum acceptance:

- written authorization exists
- no raw sensitive identifiers are published
- reviewer decisions are exported from the CE review console
- tenant is anonymized in paper results

## Reviewer Workflow

For each CE entry, CRIS-SME now emits both:

- `proposed_status`: evidence-support label, such as `supported_no_issue`, `supported_risk_found`, or `endpoint_required`
- `proposed_answer`: candidate CE answer: `Yes`, `No`, or `Cannot determine`

For direct and inferred cloud entries:

- mapped risk finding present -> proposed answer `No`
- mapped controls present with no CRIS-SME risk finding -> proposed answer `Yes`
- insufficient current evidence -> proposed answer `Cannot determine`

A proposed `Yes` is intentionally bounded. It means CRIS-SME did not observe a mapped cloud-control-plane finding for that CE entry. It does not prove that every endpoint, application-layer, inherited-rule, business-process, or non-Azure implementation path satisfies the CE requirement.

For each CE entry, reviewer records one of:

- `accepted`
- `overridden`
- `needs_evidence`
- `pending`

Reviewer should complete:

- final answer
- final status
- reviewer note
- evidence reference if external evidence is used
- override reason if the CRIS-SME proposed answer or proposed status is changed

Pending entries must remain pending. Do not force a final answer where evidence is incomplete.

Import a completed reviewer ledger with:

```bash
PYTHONPATH=src python3 scripts/import_ce_review_ledger.py \
  --answer-pack outputs/reports/cris_sme_ce_self_assessment.json \
  --ledger path/to/completed-review-ledger.csv \
  --output-dir outputs/reports/ce_review_import
```

The importer accepts CSV ledgers, JSON review-decision dictionaries, and exported review-console JSON. Imported human-review decisions contribute to `agreement_count` and `agreement_rate`; AI-assisted draft reviewers remain separated as draft acceptance.

### AI-Assisted Pilot Ledger

For internal research iteration, CRIS-SME can generate an AI-assisted pilot review ledger:

```bash
PYTHONPATH=src python3 scripts/build_ce_review_draft.py
```

This writes reviewed-draft artifacts under:

`outputs/reports/ce_review_draft/`

The draft ledger is deliberately conservative:

- direct cloud evidence entries are accepted as pilot decisions
- inferred cloud `No` entries with linked CRIS-SME risks are accepted as conservative answer-impact decisions
- inferred cloud `Yes` entries are marked `needs_evidence`
- endpoint, policy, manual, and not-observable entries remain pending

This draft must be labelled as `AI-assisted internal reviewer draft` or equivalent. It is useful for checking the workflow, paper tables, and agreement-metric plumbing, but it is not an independent human expert review. Do not report it as assessor agreement unless a CE-knowledgeable reviewer has checked and signed the decisions.

Evaluation metrics reserve `agreement_count` and `agreement_rate` for non-AI human review decisions. AI-assisted ledgers are reported separately as `draft_accepted_count` and `draft_accepted_rate` to avoid self-validation being mistaken for independent agreement.

## Metrics

### Observability Metrics

Report:

- total mapped entries
- technical-control entries
- direct cloud count
- inferred cloud count
- total cloud-supported count
- total cloud-supported rate
- technical cloud-supported count
- technical cloud-supported rate
- non-cloud evidence required count

### Evidence Gap Metrics

Report:

- endpoint-required count and rate
- policy-required count and rate
- manual-required count and rate
- not-observable count and rate
- sample question IDs per gap class

### Review Metrics

Report:

- reviewed count
- reviewed rate
- accepted count
- override count
- needs-evidence count
- pending count
- agreement evaluable count
- agreement count
- agreement rate
- draft accepted count
- draft accepted rate
- proposed answer counts
- final answer counts

Agreement denominator:
Only `accepted` and `overridden` entries are agreement-evaluable.

AI-assisted reviewer entries are excluded from the human agreement denominator and reported as draft acceptance.

`needs_evidence` entries are not disagreement. They are evidence gaps.

`pending` entries are not evaluated.

### Control Contribution Metrics

Report:

- top CRIS-SME controls contributing to CE answer-impact findings
- affected question count
- max linked score
- sample finding titles

This metric should be interpreted as answer-impact contribution, not as official CE failure count.

## Agreement Coding

Accepted:
Reviewer final answer matches CRIS-SME proposed answer.

Overridden:
Reviewer final answer differs from CRIS-SME proposed answer.

Needs evidence:
Reviewer could not validate the entry without additional evidence.

Pending:
No review decision has been made.

Agreement rate:

`matching final answers / (accepted + overridden) * 100`

The generated metrics pack computes this over accepted and overridden entries by comparing `final_answer` with `proposed_answer`.

## Evidence Retrieval Study Option

If measuring time saved, avoid measuring total CE questionnaire completion time. That depends heavily on participant familiarity.

Measure evidence retrieval time instead:

1. Select a fixed set of CE entries.
2. Ask reviewer to locate supporting evidence manually.
3. Ask reviewer to locate supporting evidence using CRIS-SME.
4. Record time to evidence reference.
5. Record whether reviewer accepted, overrode, or requested more evidence.

Suggested measures:

- median manual evidence retrieval time
- median CRIS-SME-assisted retrieval time
- number of evidence references found
- reviewer confidence score
- override rate

## Reporting Rules

Use absolute counts and percentages together.

Good:
`22 of 62 technical-control entries were cloud-supported (35.48%).`

Avoid:
`CRIS-SME automates 35.48% of Cyber Essentials.`

Use:
`cloud-supported`, `pre-populated`, `human-reviewable`, `evidence gap`.

Avoid:
`certified`, `passed`, `compliant`, unless a qualified certifying authority has made that decision.

## Reproducibility Steps

Run baseline:

```bash
PYTHONPATH=src python3 -m cris_sme.main
```

Build static site:

```bash
python3 scripts/build_pages_site.py --reports-dir outputs/reports --figures-dir outputs/figures --dist-dir dist
```

Open demo:

```bash
python3 -m http.server 8000 --directory dist/site
```

Then visit:

`http://127.0.0.1:8000/demo/#ce-workflow`

## Ethics And Data Handling

Do not publish raw tenant identifiers, subscription IDs, user names, IP addresses, resource group names, storage account names, or internal hostnames from real tenants.

Use selective disclosure and redacted evidence artifacts for sharing.

Keep raw live reports local unless there is explicit permission to publish them.

## Completion Criteria

An evaluation run is complete when:

- CRIS-SME pipeline exits successfully
- all CE artifacts exist
- review console is opened and reviewed or explicitly marked as pre-review baseline
- paper tables export exists
- metrics are recorded in the evaluation log
- limitations are documented
