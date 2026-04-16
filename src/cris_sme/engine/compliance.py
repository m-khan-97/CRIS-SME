# Compliance mapping logic for turning findings into framework-aligned outputs.
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from cris_sme.models.compliance_result import (
    ComplianceAssessmentResult,
    ComplianceMappingEntry,
    RegulatoryProfileSummary,
)
from cris_sme.models.finding import Finding


DEFAULT_COMPLIANCE_MAPPINGS_PATH = Path("data/compliance_mappings.json")
UK_SME_FRAMEWORKS = {
    "Cyber Essentials",
    "Cyber Essentials Plus",
    "UK GDPR",
    "FCA SYSC",
    "DSPT",
}


def load_compliance_mappings(
    path: str | Path = DEFAULT_COMPLIANCE_MAPPINGS_PATH,
) -> dict[str, ComplianceMappingEntry]:
    """Load the control-to-framework mapping catalog from JSON."""
    mapping_path = Path(path)
    raw_entries = json.loads(mapping_path.read_text(encoding="utf-8"))
    entries = [ComplianceMappingEntry.model_validate(item) for item in raw_entries]
    return {entry.control_id: entry for entry in entries}


def assess_compliance_mappings(
    findings: list[Finding],
    mapping_catalog: dict[str, ComplianceMappingEntry],
) -> ComplianceAssessmentResult:
    """Summarize how findings map into external compliance and governance frameworks."""
    frameworks_seen: set[str] = set()
    findings_by_framework: Counter[str] = Counter()
    control_reference_counts: dict[str, int] = {}
    mapped_findings: list[dict[str, object]] = []
    uk_frameworks_seen: set[str] = set()
    uk_findings_by_framework: Counter[str] = Counter()
    uk_mapped_control_ids: set[str] = set()
    uk_mapped_finding_count = 0

    for finding in findings:
        mapping_entry = mapping_catalog.get(finding.control_id)
        if not mapping_entry:
            continue

        control_reference_counts[finding.control_id] = len(mapping_entry.references)
        provider = str(finding.metadata.get("provider", "azure"))

        reference_items = []
        finding_has_uk_reference = False
        for reference in mapping_entry.references:
            frameworks_seen.add(reference.framework)
            if not finding.is_compliant:
                findings_by_framework[reference.framework] += 1

            if _is_uk_sme_framework(reference.framework):
                uk_frameworks_seen.add(reference.framework)
                uk_mapped_control_ids.add(finding.control_id)
                finding_has_uk_reference = True
                if not finding.is_compliant:
                    uk_findings_by_framework[reference.framework] += 1

            reference_items.append(reference.model_dump())

        if finding_has_uk_reference and not finding.is_compliant:
            uk_mapped_finding_count += 1

        mapped_findings.append(
            {
                "control_id": finding.control_id,
                "title": finding.title,
                "category": finding.category.value,
                "is_compliant": finding.is_compliant,
                "provider": provider,
                "provider_scope": mapping_entry.provider_scope,
                "references": reference_items,
            }
        )

    return ComplianceAssessmentResult(
        frameworks_covered=sorted(frameworks_seen),
        control_reference_counts=control_reference_counts,
        findings_by_framework=dict(sorted(findings_by_framework.items())),
        mapped_findings=mapped_findings,
        uk_sme_profile=RegulatoryProfileSummary(
            profile_name="UK SME regulatory profile",
            frameworks_covered=sorted(uk_frameworks_seen),
            findings_by_framework=dict(sorted(uk_findings_by_framework.items())),
            mapped_control_ids=sorted(uk_mapped_control_ids),
            mapped_control_count=len(uk_mapped_control_ids),
            mapped_finding_count=uk_mapped_finding_count,
        ),
    )


def _is_uk_sme_framework(framework_name: str) -> bool:
    """Return True when a framework belongs to the UK-focused SME compliance profile."""
    return framework_name in UK_SME_FRAMEWORKS
