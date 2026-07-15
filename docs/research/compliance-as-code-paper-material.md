# Paper Material Pack — "Compliance-as-Code for Cloud Security Baselines: Automating GDPR and Cyber Essentials Verification in Azure"

> Status: research working material, July 2026. Everything in the "Verified facts"
> sections below was checked directly against local clones of
> `~/Github/prowler` and `~/Github/checkov` and against this repository.
> Use this as source material for the manuscript write-up.

---

## 1. Status: the Prowler artifact now EXISTS (built July 2026)

The two framework files are implemented, validated, and committed on branch
`feat/azure-gdpr-cyber-essentials-compliance` of the `m-khan-97/prowler` fork
(commit `468bb4a09`):

- `prowler/compliance/azure/cyber_essentials_3.3_azure.json` —
  **18 requirements** (12 automated + 6 explicit non-automatable),
  **64 unique checks** mapped. Evidence-class distribution:
  8 direct_cloud, 4 inferred_cloud, 4 endpoint_required, 1 policy_required,
  1 manual_required.
- `prowler/compliance/azure/gdpr_azure.json` — **10 requirements**
  (8 automated + 2 explicit non-automatable) covering Articles 5(1)(f), 25,
  30, 32(1)(a–d) decomposed, 33, 34, 35; **76 unique checks** mapped.
  Distribution: 5 direct_cloud, 3 inferred_cloud, 1 policy_required,
  1 manual_required.

**Headline numbers for the paper:** the two frameworks together exercise
**107 of Prowler's 169 Azure checks (63%)**, with 33 checks shared between
the two baselines (evidence reuse across frameworks — a quantified
compliance-as-code benefit worth a sentence in the discussion).

Validation performed (all reproducible):
- every referenced check ID exists in the Azure check inventory;
- both files load through Prowler's `Compliance` pydantic model
  (attributes resolve to `Generic_Compliance_Requirement_Attribute`);
- both are discovered by `Compliance.get_bulk("azure")` — i.e. selectable as
  `--compliance cyber_essentials_3.3_azure` / `--compliance gdpr_azure`;
- Prowler's compliance test suites pass (203 passed).

Remaining step for the "publicly available" claim: push the branch and open
the upstream PRs ("under review upstream; available at fork URL" is citable
for a WIP paper).

**The gap claim in the abstract is verified and strong** (see §2): Prowler has
no Cyber Essentials framework for any provider, and its only GDPR mapping is
AWS-only and covers just 3 articles.

### Design note for the Methods section

Prowler's generic attribute schema has no evidence-class field, so the
taxonomy is carried in the generic `Type` attribute
(direct_cloud / inferred_cloud / endpoint_required / policy_required /
manual_required) with per-requirement rationale in `Comment`. Prowler's own
ASD Essential Eight framework uses a bespoke `CloudApplicability`
(full/partial/limited/non-applicable) attribute — cite it as the closest
existing idiom and argue the finer-grained taxonomy as the improvement: it
states *what kind* of evidence is missing, not merely that cloud coverage is
partial.

---

## 2. Verified facts: Prowler (v5.30.x checkout)

Compliance-as-code model:
- A "compliance framework" in Prowler is a JSON file in
  `prowler/compliance/<provider>/` with the schema:
  `{Framework, Version, Provider, Description, Requirements[]}`, where each
  requirement is `{Id, Name, Description, Attributes[], Checks[]}` and
  `Checks` is a list of existing check IDs. No code needed to add a framework.
- Azure check inventory: **169 checks across 22 services** (`aisearch, aks,
  apim, app, appinsights, containerregistry, cosmosdb, databricks, defender,
  entra, iam, keyvault, logs, monitor, mysql, network, policy, postgresql,
  recovery, sqlserver, storage, vm`).
- Azure compliance frameworks shipped today: C5, CCC, CIS 2.0–5.0, ENS
  RD2022, FedRAMP 20x KSI, HIPAA, ISO 27001:2022, MITRE ATT&CK, NIS2, PCI
  4.0, Prowler ThreatScore, RBI CSF, SecNumCloud, SOC2.
  **No GDPR. No Cyber Essentials.**
- GDPR exists only for AWS (`prowler/compliance/aws/gdpr_aws.json`) and maps
  only **3 articles** (25, 30, 32) to 42/12/25 checks respectively — coarse,
  article-level granularity with no sub-requirement decomposition and no
  treatment of non-automatable measures. This is the "prior art" to improve on.
- CIS 5.0 Azure has 155 requirements and richer per-requirement `Attributes`
  (Section, Profile, AssessmentStatus, Rationale, Audit/Remediation
  procedures) — the schema to imitate for attribute depth.

Useful critique for the paper: Prowler's requirement→check mapping is **binary
and silent about coverage quality** — a requirement with one tangentially
related check renders the same as one with complete coverage, and requirements
with zero possible checks are simply omitted or left empty with no
machine-readable statement of *why*. This is exactly where the paper's
evidence-sufficiency contribution lands (§4, §6).

## 3. Verified facts: Checkov

- Checkov is **static/pre-deployment** policy-as-code: it scans IaC (Terraform,
  ARM, Bicep, CloudFormation…) rather than live cloud posture. Azure coverage:
  **244 Terraform + 195 ARM resource checks** in
  `checkov/terraform/checks/resource/azure/` and `checkov/arm/`.
- Checks carry an internal ID (`CKV_AZURE_n`) and a category (e.g.
  `ENCRYPTION`), but **no regulatory framework mappings** — no GDPR, no Cyber
  Essentials, no CIS mapping files in the OSS repo (framework mapping is a
  feature of the commercial Prisma Cloud layer).
- Related-work positioning: Checkov verifies *intent* (what you declared);
  Prowler verifies *state* (what is actually running). Regulatory compliance
  concerns state, and drift between audits happens in state — hence a
  runtime-posture framework (Prowler) is the right contribution target. One
  sentence of this argument belongs in Related Work.

## 4. Reusable assets from CRIS-SME (this repo)

These are already built, tested (321 passing tests), and can be cited/reused
as the methodological basis:

1. **CE question-level mapping** — `data/ce_question_mapping.json`: 106
   paraphrased entries from the IASME "Danzell" v16.2 question set
   (Requirements for IT Infrastructure **v3.3**, effective 2026-04-27), each
   with an evidence class, supporting control IDs, and
   `human_review_required` flag. **Licensing caution is already handled**:
   paraphrased text only, stable local IDs, no verbatim IASME wording — keep
   this discipline in the Prowler contribution too (check descriptions must
   paraphrase, and the paper should state this).
2. **Evidence-sufficiency taxonomy** (the paper's key methodological export):
   `direct_cloud / inferred_cloud / endpoint_required / policy_required /
   manual_required / not_observable`. This answers the abstract's promise to
   describe "handling of controls that resist full automation" with a
   machine-readable classification rather than prose hand-waving.
3. **Measured CE coverage numbers** (from
   `docs/research/ce-question-coverage-analysis.md`, Azure control plane only):
   direct 5/106 (4.7%), inferred 23/106 (21.7%), endpoint-required 24/106
   (22.6%); 62 of 106 entries are technical-control entries, 28 entries
   cloud-supported overall / 22 technical entries cloud-supported. These are
   honest, already-computed numbers for the "substantial share" claim — and
   they also *bound* it: the paper must not claim majority automation of CE,
   because CE is endpoint-heavy by design.
4. **Three-mode evaluation design** (`docs/three-mode-evaluation-comparison.md`):
   synthetic baseline / live Azure tenant / controlled vulnerable lab
   (AzureGoat-style, `intentionally_vulnerable_lab` authorization basis). This
   is the ready-made template for "preliminary evaluation against
   representative Azure tenants".
5. **CE self-assessment pack generator** (`src/cris_sme/engine/ce_questionnaire.py`,
   `ce_evaluation.py`, `ce_review*.py`): proposes Yes/No/Cannot-determine per
   question with a human review ledger — citable as the workflow that consumes
   the automated verification results.
6. **Existing paper skeleton** (`docs/research/cyber-essentials-paper-skeleton.md`)
   — note its framing is deliberately narrower ("pre-population, not
   certification"). The new paper's broader "automating verification" framing
   must keep the same guardrails: **verification of technical controls, never
   certification of the scheme**.

## 5. Draft mapping: CE v3.3 five controls → existing Prowler Azure checks

This is the seed of `cyber_essentials_3.3_azure.json`. All check IDs verified
present in the local Prowler checkout. Coverage class uses the CRIS-SME
taxonomy.

### CE-1 Firewalls (boundary + host)
`direct_cloud`: `network_ssh_internet_access_restricted`,
`network_rdp_internet_access_restricted`, `network_http_internet_access_restricted`,
`network_udp_internet_access_restricted`, `sqlserver_unrestricted_inbound_access`,
`storage_account_public_network_access_disabled`,
`storage_default_network_access_rule_is_denied`,
`cosmosdb_account_firewall_use_selected_networks`,
`aks_clusters_public_access_disabled`, `containerregistry_not_publicly_accessible`,
`app_function_not_publicly_accessible`, `aisearch_service_not_publicly_accessible`.
`policy_required`: documented business need for each open service;
host firewalls on end-user devices → `endpoint_required`.

### CE-2 Secure configuration
`direct_cloud`: `entra_security_defaults_enabled`,
`storage_secure_transfer_required_is_enabled`,
`storage_ensure_minimum_tls_version_12`, `app_minimum_tls_version_12`,
`mysql_flexible_server_minimum_tls_version_12`,
`sqlserver_recommended_minimal_tls_version`,
`app_ensure_http_is_redirected_to_https`, `app_ftp_deployment_disabled`,
`containerregistry_admin_user_disabled`, `storage_account_key_access_disabled`,
`vm_linux_enforce_ssh_authentication`, `keyvault_rbac_enabled`.
Default-password removal on devices, autorun disabling → `endpoint_required`.
Device unlock/PIN policy → `endpoint_required` + `policy_required`.

### CE-3 User access control
`direct_cloud`: `entra_privileged_user_has_mfa`, `entra_non_privileged_user_has_mfa`,
`entra_conditional_access_policy_require_mfa_for_admin_portals`,
`entra_conditional_access_policy_require_mfa_for_management_api`,
`entra_global_admin_in_less_than_five_users`,
`entra_policy_guest_users_access_restrictions`,
`iam_subscription_roles_owner_custom_not_created`,
`iam_role_user_access_admin_restricted`, `sqlserver_azuread_administrator_enabled`,
`cosmosdb_account_use_aad_and_rbac`, `vm_jit_access_enabled`,
`entra_user_with_vm_access_has_mfa`.
Joiner/leaver process, admin-account separation policy → `policy_required`.

### CE-4 Malware protection
`inferred_cloud` (control-plane signal ≠ endpoint state — flag this in the
attribute notes): `defender_ensure_defender_for_server_is_on`,
`defender_assessments_vm_endpoint_protection_installed`,
`defender_ensure_wdatp_is_enabled`, `defender_ensure_defender_for_storage_is_on`,
`defender_ensure_mcas_is_enabled`.
End-user device AV, allow-listing → `endpoint_required`.

### CE-5 Security update management
`direct_cloud`/`inferred_cloud`: `defender_ensure_system_updates_are_applied`,
`app_ensure_java_version_is_latest`, `app_ensure_php_version_is_latest`,
`app_ensure_python_version_is_latest`, `app_function_latest_runtime_version`,
`vm_ensure_using_approved_images`,
`defender_auto_provisioning_vulnerabilty_assessments_machines_on`,
`sqlserver_va_periodic_recurring_scans_enabled`.
14-day patch SLA for end-user devices, unsupported-software removal →
`endpoint_required` + `policy_required`.

**Headline count for the paper:** ~45–50 of Prowler's 169 Azure checks map to
CE technical requirements with direct or inferred coverage; every remaining CE
requirement receives an explicit non-automatable classification instead of
being dropped. (Recount precisely when the JSON is final.)

## 6. Draft mapping: GDPR technical articles → Prowler Azure checks

Scope to the technical-measures articles (mirroring but deepening the AWS
precedent, which stops at 3 articles):

| Article | Theme | Example Prowler Azure checks | Class |
|---|---|---|---|
| 5(1)(f) | Integrity & confidentiality | `storage_infrastructure_encryption_is_enabled`, `sqlserver_tde_encryption_enabled`, `vm_ensure_attached_disks_encrypted_with_cmk`, all TLS-minimum checks | direct |
| 25 | Data protection by design/default | `storage_blob_public_access_level_is_disabled`, `entra_security_defaults_enabled`, `network_*_internet_access_restricted`, `keyvault_rbac_enabled` | direct |
| 30 | Records of processing activities | `monitor_diagnostic_settings_exists`, `sqlserver_auditing_enabled`, `sqlserver_auditing_retention_90_days`, `mysql_flexible_server_audit_log_enabled`, `keyvault_logging_enabled` | inferred — logs support but do not constitute Art. 30 records |
| 32 | Security of processing | MFA family (`entra_*_has_mfa`), encryption family, `vm_backup_enabled`, `vm_sufficient_daily_backup_retention_period`, `storage_geo_redundant_enabled`, `cosmosdb_account_automatic_failover_enabled` (resilience limb of 32(1)(b–c)) | direct/inferred |
| 33–34 | Breach notification readiness | `defender_additional_email_configured_with_a_security_contact`, `defender_ensure_notify_alerts_severity_is_high`, `defender_ensure_notify_emails_to_owners`, `monitor_alert_*` family | inferred — detection/alerting capability, not the 72-hour process |
| 35 | DPIA | none | `policy_required` — explicitly listed as non-automatable |

The Art. 30/33/35 rows are where the paper's "limitations of automated
interpretation of legal requirements" discussion becomes concrete rather than
generic: logging *evidence* vs. legal *records*, alerting *capability* vs.
notification *obligation*.

## 7. Evaluation design (maps to "preliminary evaluation" in the abstract)

Environments already available to this project:
1. **Live Azure tenant** (authorized; used for the IoMT and CE tracks).
2. **Controlled vulnerable lab** (AzureGoat-style; `docs/azuregoat-lab-guide.md`).
3. **Synthetic/mock baseline** for reproducibility.

Metrics to report:
- **Coverage**: % of framework requirements with ≥1 mapped check, split by
  evidence class (the honest headline; cite CRIS-SME's measured CE numbers as
  the methodology's precedent).
- **Assessment effort**: wall-clock scan time vs. documented manual-audit
  baseline (justify "days to minutes" — cite a manual CE self-assessment
  effort estimate from IASME/NCSC practitioner guidance, or measure your own
  time-to-complete on the live tenant).
- **Drift detection**: introduce a misconfiguration in the lab between two
  scans; show detection delta. The vulnerable-lab track exists precisely for
  this.
- **Mapping validity** (optional but strong): expert review of a mapping
  sample, echoing the IoMT expert-review-pack method already used in this repo.

## 8. Limitations material (the abstract promises all three)

1. **Legal interpretation**: a check verifies a *technical proxy* for a legal
   requirement; the mapping encodes an interpretation, not the law. Mitigation:
   evidence classes + per-requirement rationale attributes; never emit
   "compliant with GDPR", only "technical measures verified/not verified".
2. **Provider API churn**: quantify with Prowler's own git history (checks are
   renamed/added every release; the AWS GDPR file references checks by string
   ID with no CI guarantee they still exist — a measurable fragility; consider
   contributing a CI validation test as a bonus artifact).
3. **Organisational/procedural measures**: the endpoint/policy/manual classes;
   report their share explicitly (for CE it is the majority — say so plainly).
4. **CE is endpoint-heavy**: cloud posture covers the infrastructure slice
   only; scope the claim to "cloud-hosted infrastructure within CE scope".

## 9. Related work table (draft)

| Tool/approach | Layer | Azure | GDPR mapping | Cyber Essentials | Non-automatable handling |
|---|---|---|---|---|---|
| Prowler (OSS) | Runtime posture | 169 checks | AWS only, 3 articles | none | omitted silently |
| Checkov (OSS) | IaC static | 244 TF + 195 ARM checks | none (commercial layer) | none | n/a |
| Microsoft Defender for Cloud | Runtime posture | native | regulatory-standards feature; closed mappings | none | manual attestation slots |
| CRIS-SME (this group) | Runtime posture + governance | 6 domains | UK GDPR crosswalk | 106-question mapping | 6-class evidence taxonomy |
| **This paper** | Runtime posture | Prowler-based | Azure, article-decomposed | v3.3, five controls | machine-readable classes |

## 10. Suggested structure for the WIP paper (6 pages typical)

1. **Introduction** (¾ p) — drift between point-in-time audits; SME translation
   burden; contributions list (mapping methodology, two framework files,
   evidence-sufficiency classes, preliminary eval, public artifact).
2. **Background & related work** (¾ p) — §3 + §9 material; the
   Prowler-AWS-GDPR precedent and its 3-article shallowness as the foil.
3. **Mapping methodology** (1¼ p) — requirement decomposition → candidate
   check identification → evidence-class assignment → rationale attributes;
   the paraphrase/licensing discipline for IASME text.
4. **Implementation** (1 p) — Prowler framework JSON schema; the two
   contributed files; counts per framework and per evidence class; missing
   checks identified (candidates for new Python checks as future
   contribution).
5. **Preliminary evaluation** (1 p) — §7 metrics on live tenant + lab.
6. **Discussion & limitations** (¾ p) — §8.
7. **Roadmap & conclusion** (½ p) — multi-framework (DSPT, NIS2 overlap),
   remediation guidance, AWS/GCP ports, upstream merge status.

## 11. Paper framing decision: general (two implementations) vs Prowler-only

**Recommendation: general framing — one methodology, two implementations.**

Structure the paper around the *evidence-sufficiency-aware compliance-as-code
methodology*, instantiated twice:

1. **CRIS-SME** (reference implementation): supplies all the empirical depth —
   106-question CE mapping, measured coverage on a live Azure tenant, the
   three-mode evaluation (synthetic / live / vulnerable lab), human review
   ledger, 321 passing tests. This is where the "good amount of data" lives;
   a Prowler-only paper would have to abandon it.
2. **Prowler contribution** (portability + adoption artifact): proves the
   methodology is not CRIS-SME-specific — it retrofits onto the most widely
   used OSS CSPM with zero code changes (pure JSON), and gives reviewers a
   public, independently runnable artifact with big-community reach.

Why this beats Prowler-only:
- A Prowler-only paper reduces to "we wrote two mapping files" — thin for
  reviewers. The methodology + measured evaluation is the actual contribution.
- The two-implementation story directly answers the generality question every
  reviewer asks ("does this only work in your tool?").
- The abstract needs only light edits: "implemented in an open-source
  assessment engine (CRIS-SME) and contributed as compliance framework
  mappings to Prowler" instead of "implemented as contributions to Prowler".

Keep the CE-certification guardrail in both halves: verification of technical
controls, never certification of the scheme.

## 12. Immediate next actions

1. ~~Build the two framework files~~ **Done** — branch
   `feat/azure-gdpr-cyber-essentials-compliance`, commit `468bb4a09`.
2. Push the branch; open the two upstream PRs (one per framework is easier to
   review than one combined PR).
3. Run Prowler with `--compliance cyber_essentials_3.3_azure` and
   `--compliance gdpr_azure` against the live tenant and the vulnerable lab;
   capture timings and drift-detection results for §7. (Needs Prowler's deps
   installed: `pip install -e .` or `uv sync` in the fork — the CLI currently
   fails on missing `alive_progress` in this environment.)
4. Confirm the IASME licensing position for paraphrased requirement text in an
   upstream OSS contribution (the CRIS-SME paraphrase discipline is already
   applied in the file; Prowler maintainers may still ask).
5. Rewrite the abstract per §11 and draft the manuscript from §10.
