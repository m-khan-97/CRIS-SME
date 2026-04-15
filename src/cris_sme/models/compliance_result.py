# Compliance mapping models for translating findings into framework-aligned outputs.
from __future__ import annotations

from pydantic import BaseModel, Field


class ComplianceReference(BaseModel):
    """A single framework reference associated with a control or finding."""

    framework: str = Field(..., min_length=2)
    reference_id: str = Field(..., min_length=2)
    title: str = Field(..., min_length=3)
    relevance: str = Field(..., min_length=3)


class ComplianceMappingEntry(BaseModel):
    """Catalog entry describing how a CRIS-SME control maps to frameworks."""

    control_id: str = Field(..., min_length=3)
    category: str = Field(..., min_length=2)
    provider_scope: str = Field(..., min_length=2)
    references: list[ComplianceReference] = Field(default_factory=list)


class ComplianceAssessmentResult(BaseModel):
    """Compliance summary generated from mapped findings."""

    frameworks_covered: list[str] = Field(default_factory=list)
    control_reference_counts: dict[str, int] = Field(default_factory=dict)
    findings_by_framework: dict[str, int] = Field(default_factory=dict)
    mapped_findings: list[dict[str, object]] = Field(default_factory=list)
