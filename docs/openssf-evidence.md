# OpenSSF Passing Evidence Register

Reviewed 26 September 2026 against the
[official Passing criteria](https://www.bestpractices.dev/en/criteria/0).
Each official criterion identifier has its own row; consult the source for its
normative wording, applicability and badge scoring. This is an internal
preparation register, not an OpenSSF assessment or badge application.

**Evidence** means a concrete local/repository artifact is available for review;
**Partial** means evidence or execution is incomplete; **Open** means no sufficient
review has been recorded. None of these means an official criterion is met.
No automatic percentage, N/A decisions or badge claims are produced.

The current owner for follow-up is the project maintainer identified in
[GOVERNANCE.md](../GOVERNANCE.md). Operational claims need dated observations,
not only policies. Recheck the official criterion set before applying; the
offline regression check detects accidental removal of this 67-identifier
snapshot but does not detect upstream changes.

## Criterion Register

| Official identifier | Internal state | Evidence / starting point | Gap or interpretation |
| --- | --- | --- | --- |
| `description_good` | Partial | [README.md](../README.md), [CONTRIBUTING.md](../CONTRIBUTING.md) | Documentation is present; review it with a first-time contributor before claiming completion. |
| `interact` | Partial | [README.md](../README.md), [CONTRIBUTING.md](../CONTRIBUTING.md) | Documentation is present; review it with a first-time contributor before claiming completion. |
| `contribution` | Partial | [README.md](../README.md), [CONTRIBUTING.md](../CONTRIBUTING.md) | Documentation is present; review it with a first-time contributor before claiming completion. |
| `contribution_requirements` | Partial | [README.md](../README.md), [CONTRIBUTING.md](../CONTRIBUTING.md) | Documentation is present; review it with a first-time contributor before claiming completion. |
| `floss_license` | Partial | [LICENSE](../LICENSE), [docs/dependency-licenses.md](../docs/dependency-licenses.md) | Root MIT declaration is present. Third-party distributions and research/customer material still need rights review. |
| `floss_license_osi` | Partial | [LICENSE](../LICENSE), [docs/dependency-licenses.md](../docs/dependency-licenses.md) | Root MIT declaration is present. Third-party distributions and research/customer material still need rights review. |
| `license_location` | Partial | [LICENSE](../LICENSE), [docs/dependency-licenses.md](../docs/dependency-licenses.md) | Root MIT declaration is present. Third-party distributions and research/customer material still need rights review. |
| `documentation_basics` | Partial | [README.md](../README.md), [docs/architecture.md](../docs/architecture.md) | Setup and architecture exist; check interface completeness against actual API, CLI and export behavior. |
| `documentation_interface` | Partial | [README.md](../README.md), [docs/architecture.md](../docs/architecture.md) | Setup and architecture exist; check interface completeness against actual API, CLI and export behavior. |
| `sites_https` | Open | [README.md](../README.md) | Inventory and verify every published site/download endpoint; repository HTTPS alone is insufficient evidence. |
| `discussion` | Evidence | [CONTRIBUTING.md](../CONTRIBUTING.md), [SUPPORT.md](../SUPPORT.md) | Public GitHub issues and English contribution guidance provide the documented route; do not send sensitive reports there. |
| `english` | Evidence | [CONTRIBUTING.md](../CONTRIBUTING.md), [SUPPORT.md](../SUPPORT.md) | Public GitHub issues and English contribution guidance provide the documented route; do not send sensitive reports there. |
| `report_process` | Evidence | [CONTRIBUTING.md](../CONTRIBUTING.md), [SUPPORT.md](../SUPPORT.md) | Public GitHub issues and English contribution guidance provide the documented route; do not send sensitive reports there. |
| `report_tracker` | Evidence | [CONTRIBUTING.md](../CONTRIBUTING.md), [SUPPORT.md](../SUPPORT.md) | Public GitHub issues and English contribution guidance provide the documented route; do not send sensitive reports there. |
| `report_archive` | Evidence | [CONTRIBUTING.md](../CONTRIBUTING.md), [SUPPORT.md](../SUPPORT.md) | Public GitHub issues and English contribution guidance provide the documented route; do not send sensitive reports there. |
| `maintained` | Evidence | [GOVERNANCE.md](../GOVERNANCE.md) | Public Git history includes incremental development; 8eb0595 was pushed on 26 September 2026. Continuity beyond one owner remains open. |
| `repo_public` | Evidence | [GOVERNANCE.md](../GOVERNANCE.md) | Public Git history includes incremental development; 8eb0595 was pushed on 26 September 2026. Continuity beyond one owner remains open. |
| `repo_track` | Evidence | [GOVERNANCE.md](../GOVERNANCE.md) | Public Git history includes incremental development; 8eb0595 was pushed on 26 September 2026. Continuity beyond one owner remains open. |
| `repo_interim` | Evidence | [GOVERNANCE.md](../GOVERNANCE.md) | Public Git history includes incremental development; 8eb0595 was pushed on 26 September 2026. Continuity beyond one owner remains open. |
| `repo_distributed` | Evidence | [GOVERNANCE.md](../GOVERNANCE.md) | Public Git history includes incremental development; 8eb0595 was pushed on 26 September 2026. Continuity beyond one owner remains open. |
| `version_unique` | Open | [.github/workflows/release.yml](../.github/workflows/release.yml) | Release workflow exists, but no published GitHub release was returned on 26 September. Verify tags, artifact/version alignment and authored upgrade/security notes. |
| `version_semver` | Open | [.github/workflows/release.yml](../.github/workflows/release.yml) | Release workflow exists, but no published GitHub release was returned on 26 September. Verify tags, artifact/version alignment and authored upgrade/security notes. |
| `version_tags` | Open | [.github/workflows/release.yml](../.github/workflows/release.yml) | Release workflow exists, but no published GitHub release was returned on 26 September. Verify tags, artifact/version alignment and authored upgrade/security notes. |
| `release_notes` | Open | [.github/workflows/release.yml](../.github/workflows/release.yml) | Release workflow exists, but no published GitHub release was returned on 26 September. Verify tags, artifact/version alignment and authored upgrade/security notes. |
| `release_notes_vulns` | Open | [.github/workflows/release.yml](../.github/workflows/release.yml) | Release workflow exists, but no published GitHub release was returned on 26 September. Verify tags, artifact/version alignment and authored upgrade/security notes. |
| `report_responses` | Open | [SUPPORT.md](../SUPPORT.md) | No dated issue-response sample has been assessed. A policy does not establish historical responsiveness. |
| `enhancement_responses` | Open | [SUPPORT.md](../SUPPORT.md) | No dated issue-response sample has been assessed. A policy does not establish historical responsiveness. |
| `vulnerability_report_process` | Partial | [SECURITY.md](../SECURITY.md) | Policy describes the gap and safe contact request. Private reporting was disabled on 26 September; activate and test confidential intake. |
| `vulnerability_report_private` | Partial | [SECURITY.md](../SECURITY.md) | Policy describes the gap and safe contact request. Private reporting was disabled on 26 September; activate and test confidential intake. |
| `vulnerability_report_response` | Open | [SECURITY.md](../SECURITY.md) | Acknowledgment target is documented; no report-handling history has been measured. |
| `build` | Partial | [docs/packaging-and-container.md](../docs/packaging-and-container.md), [docs/quality-baseline.md](../docs/quality-baseline.md) | Local sdist/wheel and console builds passed; review all distribution toolchains and retain clean hosted build evidence. |
| `build_common_tools` | Partial | [docs/packaging-and-container.md](../docs/packaging-and-container.md), [docs/quality-baseline.md](../docs/quality-baseline.md) | Local sdist/wheel and console builds passed; review all distribution toolchains and retain clean hosted build evidence. |
| `build_floss_tools` | Partial | [docs/packaging-and-container.md](../docs/packaging-and-container.md), [docs/quality-baseline.md](../docs/quality-baseline.md) | Local sdist/wheel and console builds passed; review all distribution toolchains and retain clean hosted build evidence. |
| `test` | Evidence | [CONTRIBUTING.md](../CONTRIBUTING.md), [docs/quality-baseline.md](../docs/quality-baseline.md) | Documented automated checks and 22 new capability-register tests accompany the latest capability implementation. |
| `test_invocation` | Evidence | [CONTRIBUTING.md](../CONTRIBUTING.md), [docs/quality-baseline.md](../docs/quality-baseline.md) | Documented automated checks and 22 new capability-register tests accompany the latest capability implementation. |
| `test_policy` | Evidence | [CONTRIBUTING.md](../CONTRIBUTING.md), [docs/quality-baseline.md](../docs/quality-baseline.md) | Documented automated checks and 22 new capability-register tests accompany the latest capability implementation. |
| `tests_are_added` | Evidence | [CONTRIBUTING.md](../CONTRIBUTING.md), [docs/quality-baseline.md](../docs/quality-baseline.md) | Documented automated checks and 22 new capability-register tests accompany the latest capability implementation. |
| `tests_documented_added` | Evidence | [CONTRIBUTING.md](../CONTRIBUTING.md), [docs/quality-baseline.md](../docs/quality-baseline.md) | Documented automated checks and 22 new capability-register tests accompany the latest capability implementation. |
| `test_most` | Partial | [docs/quality-baseline.md](../docs/quality-baseline.md) | Package branch coverage is 65.87%; console branches are 45%. Uncovered interactions and critical negative paths need work. |
| `test_continuous_integration` | Partial | [.github/workflows/pr-validation.yml](../.github/workflows/pr-validation.yml) | PR gates are configured; the current gate needs hosted evidence and required merge protection. |
| `warnings` | Partial | [docs/quality-baseline.md](../docs/quality-baseline.md) | Frontend full lint and selected backend checks pass. Backend Ruff remains F/E9-only; dependency warnings and wider typing remain tracked. |
| `warnings_fixed` | Partial | [docs/quality-baseline.md](../docs/quality-baseline.md) | Frontend full lint and selected backend checks pass. Backend Ruff remains F/E9-only; dependency warnings and wider typing remain tracked. |
| `warnings_strict` | Partial | [docs/quality-baseline.md](../docs/quality-baseline.md) | Frontend full lint and selected backend checks pass. Backend Ruff remains F/E9-only; dependency warnings and wider typing remain tracked. |
| `know_secure_design` | Open | [docs/threat-model.md](../docs/threat-model.md) | Threat analysis is documented; a primary developer must confirm the actual knowledge criteria. Do not infer qualifications from generated policy text. |
| `know_common_errors` | Open | [docs/threat-model.md](../docs/threat-model.md) | Threat analysis is documented; a primary developer must confirm the actual knowledge criteria. Do not infer qualifications from generated policy text. |
| `crypto_published` | Open | [docs/threat-model.md](../docs/threat-model.md) | Audit cryptographic call sites, signing keys, transport and random generation. Determine applicability per criterion; no blanket crypto approval or N/A. |
| `crypto_call` | Open | [docs/threat-model.md](../docs/threat-model.md) | Audit cryptographic call sites, signing keys, transport and random generation. Determine applicability per criterion; no blanket crypto approval or N/A. |
| `crypto_floss` | Open | [docs/threat-model.md](../docs/threat-model.md) | Audit cryptographic call sites, signing keys, transport and random generation. Determine applicability per criterion; no blanket crypto approval or N/A. |
| `crypto_keylength` | Open | [docs/threat-model.md](../docs/threat-model.md) | Audit cryptographic call sites, signing keys, transport and random generation. Determine applicability per criterion; no blanket crypto approval or N/A. |
| `crypto_working` | Open | [docs/threat-model.md](../docs/threat-model.md) | Audit cryptographic call sites, signing keys, transport and random generation. Determine applicability per criterion; no blanket crypto approval or N/A. |
| `crypto_weaknesses` | Open | [docs/threat-model.md](../docs/threat-model.md) | Audit cryptographic call sites, signing keys, transport and random generation. Determine applicability per criterion; no blanket crypto approval or N/A. |
| `crypto_pfs` | Open | [docs/threat-model.md](../docs/threat-model.md) | Audit cryptographic call sites, signing keys, transport and random generation. Determine applicability per criterion; no blanket crypto approval or N/A. |
| `crypto_password_storage` | Open | [docs/threat-model.md](../docs/threat-model.md) | Audit cryptographic call sites, signing keys, transport and random generation. Determine applicability per criterion; no blanket crypto approval or N/A. |
| `crypto_random` | Open | [docs/threat-model.md](../docs/threat-model.md) | Audit cryptographic call sites, signing keys, transport and random generation. Determine applicability per criterion; no blanket crypto approval or N/A. |
| `delivery_mitm` | Open | [.github/workflows/release.yml](../.github/workflows/release.yml) | Audit source, package and artifact retrieval/verification paths; release-signature and provenance gates remain pending. |
| `delivery_unsigned` | Open | [.github/workflows/release.yml](../.github/workflows/release.yml) | Audit source, package and artifact retrieval/verification paths; release-signature and provenance gates remain pending. |
| `vulnerabilities_fixed_60_days` | Open | [SECURITY.md](../SECURITY.md), [docs/threat-model.md](../docs/threat-model.md) | Need vulnerability inventory, severity/age triage and remediation history. Documented restrictions alone do not close findings. |
| `vulnerabilities_critical_fixed` | Open | [SECURITY.md](../SECURITY.md), [docs/threat-model.md](../docs/threat-model.md) | Need vulnerability inventory, severity/age triage and remediation history. Documented restrictions alone do not close findings. |
| `no_leaked_credentials` | Open | [SECURITY.md](../SECURITY.md) | GitHub secret scanning and push protection reported disabled on 26 September. Review history and enable appropriate scanning; do not claim secrets are absent. |
| `static_analysis` | Partial | [.github/workflows/codeql.yml](../.github/workflows/codeql.yml), [docs/quality-baseline.md](../docs/quality-baseline.md) | Python CodeQL is configured, but actual execution/findings and release enforcement need verification. Frontend CodeQL is not configured. |
| `static_analysis_common_vulnerabilities` | Partial | [.github/workflows/codeql.yml](../.github/workflows/codeql.yml), [docs/quality-baseline.md](../docs/quality-baseline.md) | Python CodeQL is configured, but actual execution/findings and release enforcement need verification. Frontend CodeQL is not configured. |
| `static_analysis_fixed` | Partial | [.github/workflows/codeql.yml](../.github/workflows/codeql.yml), [docs/quality-baseline.md](../docs/quality-baseline.md) | Python CodeQL is configured, but actual execution/findings and release enforcement need verification. Frontend CodeQL is not configured. |
| `static_analysis_often` | Partial | [.github/workflows/codeql.yml](../.github/workflows/codeql.yml), [docs/quality-baseline.md](../docs/quality-baseline.md) | Python CodeQL is configured, but actual execution/findings and release enforcement need verification. Frontend CodeQL is not configured. |
| `dynamic_analysis` | Partial | [frontend/console/e2e/console.spec.ts](../frontend/console/e2e/console.spec.ts), [docs/quality-baseline.md](../docs/quality-baseline.md) | Fixture browser checks and assertion-based tests exist; they are not a completed security/fuzzing campaign or adjudicated vulnerability history. |
| `dynamic_analysis_unsafe` | Partial | [frontend/console/e2e/console.spec.ts](../frontend/console/e2e/console.spec.ts), [docs/quality-baseline.md](../docs/quality-baseline.md) | Fixture browser checks and assertion-based tests exist; they are not a completed security/fuzzing campaign or adjudicated vulnerability history. |
| `dynamic_analysis_enable_assertions` | Partial | [frontend/console/e2e/console.spec.ts](../frontend/console/e2e/console.spec.ts), [docs/quality-baseline.md](../docs/quality-baseline.md) | Fixture browser checks and assertion-based tests exist; they are not a completed security/fuzzing campaign or adjudicated vulnerability history. |
| `dynamic_analysis_fixed` | Partial | [frontend/console/e2e/console.spec.ts](../frontend/console/e2e/console.spec.ts), [docs/quality-baseline.md](../docs/quality-baseline.md) | Fixture browser checks and assertion-based tests exist; they are not a completed security/fuzzing campaign or adjudicated vulnerability history. |

## Highest-Priority Closure Work

Local release preparation now checks existing tag/source/version alignment and
tracked authored notes, with 22 regression cases. The workflow creates drafts
for maintainer review and installs its console build dependencies explicitly.
These improvements do not close the release-history rows above: no actual
release, independent approval or signed artifact has been produced. See
[release preparation](releases/README.md).
The release workflow now depends on the full reusable quality suite and packages
license inventories plus SHA-256 checksums. Local validation covers 12 additional
checksum cases; no hosted release or signed-provenance claim follows from this.

1. Activate and test confidential vulnerability intake; retain non-sensitive
   proof of delivery and acknowledgment. Do not invent response history.
2. Enable appropriate secret scanning and push protection, inspect historical
   exposure safely, and triage any discoveries without logging credentials.
3. Run the full PR matrix and container gate remotely; configure required merge
   checks and document who can bypass them.
4. Establish a consenting backup maintainer and a release/incident handover.
5. Review dependency/license inventories, notices and distributable file scope.
6. Audit cryptographic use and security findings, recording applicability and
   remediation dates. A zero-advisory npm snapshot is not a vulnerability audit.
7. Produce an actual versioned release with reviewed notes, source/artifact
   identity and retained validation evidence.

OWASP project participation, OpenSSF Best Practices, OSPS Baseline and Scorecard
are distinct tracks. No affiliation or certification is claimed here. See the
[roadmap](roadmap.md) for their separate gates.
