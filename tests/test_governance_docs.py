from pathlib import Path

from markdown_it import MarkdownIt

from scripts.check_docs import ENTRYPOINTS, validate_docs


ROOT = Path(__file__).resolve().parents[1]
# Snapshot of official Passing identifiers checked on 2026-09-26.
PASSING_IDS = {
    "description_good",
    "interact",
    "contribution",
    "contribution_requirements",
    "floss_license",
    "floss_license_osi",
    "license_location",
    "documentation_basics",
    "documentation_interface",
    "sites_https",
    "discussion",
    "english",
    "report_process",
    "report_tracker",
    "report_archive",
    "maintained",
    "repo_public",
    "repo_track",
    "repo_interim",
    "repo_distributed",
    "version_unique",
    "version_semver",
    "version_tags",
    "release_notes",
    "release_notes_vulns",
    "report_responses",
    "enhancement_responses",
    "vulnerability_report_process",
    "vulnerability_report_private",
    "vulnerability_report_response",
    "build",
    "build_common_tools",
    "build_floss_tools",
    "test",
    "test_invocation",
    "test_policy",
    "tests_are_added",
    "tests_documented_added",
    "test_most",
    "test_continuous_integration",
    "warnings",
    "warnings_fixed",
    "warnings_strict",
    "know_secure_design",
    "know_common_errors",
    "crypto_published",
    "crypto_call",
    "crypto_floss",
    "crypto_keylength",
    "crypto_working",
    "crypto_weaknesses",
    "crypto_pfs",
    "crypto_password_storage",
    "crypto_random",
    "delivery_mitm",
    "delivery_unsigned",
    "vulnerabilities_fixed_60_days",
    "vulnerabilities_critical_fixed",
    "no_leaked_credentials",
    "static_analysis",
    "static_analysis_common_vulnerabilities",
    "static_analysis_fixed",
    "static_analysis_often",
    "dynamic_analysis",
    "dynamic_analysis_unsafe",
    "dynamic_analysis_enable_assertions",
    "dynamic_analysis_fixed",
}


def test_passing_register_has_each_criterion_once() -> None:
    lines = (ROOT / "docs/openssf-evidence.md").read_text().splitlines()
    rows = [line.split("|")[1].strip().strip("`") for line in lines if line.startswith("| `")]
    assert len(rows) == len(set(rows)) == 67
    assert set(rows) == PASSING_IDS


def test_governance_documents_are_in_link_gate() -> None:
    required = {"CONTRIBUTING.md", "SECURITY.md", "SUPPORT.md", "GOVERNANCE.md",
                "docs/openssf-evidence.md", "docs/dependency-licenses.md"}
    assert required.issubset(ENTRYPOINTS)
    assert validate_docs(ROOT, tuple(required)) == []


def test_register_local_evidence_links_exist() -> None:
    document = ROOT / "docs/openssf-evidence.md"
    # Enable tables so links within register cells are also checked.
    parser = MarkdownIt("commonmark").enable("table")
    links = []
    for token in parser.parse(document.read_text()):
        for child in token.children or []:
            if child.type == "link_open":
                links.append(child.attrGet("href"))
    for target in links:
        if target and target.startswith("../"):
            assert (document.parent / target).is_file(), target
    assert len(links) >= 67
