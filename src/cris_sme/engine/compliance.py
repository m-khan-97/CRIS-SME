# Compliance mapping logic for turning findings into framework-aligned outputs.
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from cris_sme.models.compliance_result import (
    ComplianceAssessmentResult,
    ComplianceMappingEntry,
)
from cris_sme.models.finding import Finding


DEFAULT_COMPLIANCE_MAPPINGS_PATH = Path("data/compliance_mappings.json")


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

    for finding in findings:
        mapping_entry = mapping_catalog.get(finding.control_id)
        if not mapping_entry:
            continue

        control_reference_counts[finding.control_id] = len(mapping_entry.references)
        provider = str(finding.metadata.get("provider", "azure"))

        reference_items = []
        for reference in mapping_entry.references:
            frameworks_seen.add(reference.framework)
            if not finding.is_compliant:
                findings_by_framework[reference.framework] += 1

            reference_items.append(reference.model_dump())

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
    )
