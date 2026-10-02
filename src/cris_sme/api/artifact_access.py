"""Local report export policy, not user or tenant authorization."""
import os
import re
import stat
from pathlib import Path

MAX_ARTIFACT_BYTES = 32 * 1024 * 1024
MAX_REPORT_BYTES = 16 * 1024 * 1024


class ArtifactTooLarge(ValueError):
    """An artifact exceeds the local API's bounded-read budget."""


REPORT_FILES = frozenset({
    "report.html", "assurance.html", "evidence-room.html", "results_appendix.md",
    "prioritized_risks.csv",
    *[f"cris_sme_{stem}.json" for stem in (
        "report", "assessment_summary", "dashboard_payload", "evidence_snapshot",
        "findings_ocsf", "risk_bill_of_materials", "decision_provenance_graph",
        "claim_verification_pack", "assurance_case", "selective_disclosure",
        "ce_self_assessment", "ce_review_console", "ce_evaluation_metrics",
        "ce_chart_data", "public_exposure", "30_day_action_plan",
        "benchmark_observation", "executive_pack", "cyber_insurance_evidence",
    )],
    *[f"cris_sme_{stem}.html" for stem in (
        "report", "dashboard", "assurance_portal", "evidence_room",
        "ce_self_assessment", "ce_review_console", "ce_evaluation_metrics",
    )],
    *[f"cris_sme_{stem}.csv" for stem in (
        "findings", "assets", "evidence", "actions", "ce_paper_tables",
        "ce_observability_summary", "ce_gap_taxonomy", "ce_section_coverage",
    )],
    *[f"cris_sme_{stem}.md" for stem in (
        "public_exposure", "30_day_action_plan", "benchmark_comparison", "executive_pack",
        "plain_language", "board_brief", "cyber_insurance_evidence", "ce_paper_tables",
    )],
    "cris_sme_summary.txt", "cris_sme_report.sarif",
    "cris_iomt_evidence_pack.json", "cris_iomt_evidence_pack.md",
})
FIGURE_FILES = frozenset({
    "live_category_scores.png", "live_priority_distribution.png", "risk_trend.png", "run_comparison.png",
    "live_category_scores.svg", "live_priority_distribution.svg", "risk_trend.svg", "run_comparison.svg",
})


def is_report_export(relative: Path) -> bool:
    parts = relative.parts
    if len(parts) == 1:
        return relative.name in REPORT_FILES
    if len(parts) != 2:
        return False
    if parts[0] == "history":
        return bool(re.fullmatch(r"cris_sme_report_[0-9]{8}T[0-9]{6}Z\.json", parts[1]))
    if parts[0] == "figures":
        return parts[1] in FIGURE_FILES
    if parts[0] == "remediation_scripts":
        return parts[1] in {
            "cris_sme_remediation_manifest.json", "cris_sme_remediation_azure_cli.sh",
            "cris_sme_remediation_aws_cli.sh",
        }
    return False


def read_regular_file(root: Path, relative: Path, *, max_bytes: int = MAX_ARTIFACT_BYTES) -> bytes:
    """Walk an anchored directory descriptor, rejecting links and special files.

    Local writers remain trusted. Descriptor-relative opens prevent symlink
    replacement between path validation and file opening on supported POSIX hosts.
    """
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 1:
        raise ValueError("max_bytes must be a positive integer")
    if relative.is_absolute() or not relative.parts or any(
        part.startswith(".") for part in relative.parts
    ):
        raise ValueError("Invalid artifact path")
    if not hasattr(os, "O_NOFOLLOW") or os.open not in os.supports_dir_fd:
        raise OSError("Secure artifact reads require POSIX descriptor-relative opens")
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in relative.parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        descriptor = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=directory)
        with os.fdopen(descriptor, "rb") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError("Artifact is not a regular file")
            if metadata.st_size > max_bytes:
                raise ArtifactTooLarge("Artifact exceeds the local API size limit")
            # The file can grow after fstat; never use an unbounded read here.
            body = stream.read(max_bytes + 1)
            if len(body) > max_bytes:
                raise ArtifactTooLarge("Artifact exceeds the local API size limit")
            return body
    finally:
        os.close(directory)
