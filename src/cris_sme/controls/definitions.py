# Typed CRIS-SME control metadata v2 models.
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from cris_sme.models.finding import (
    FindingCategory,
    FindingSeverity,
    RemediationCostTier,
)


DEFAULT_CONTROL_METADATA_V2_PATH = Path("data/control_metadata_v2.json")
SUPPORTED_PROVIDER_STATUSES = {
    "active",
    "planned",
    "research_preview",
    "unsupported",
}


class ComplianceMappingDefinition(BaseModel):
    """Structured framework mapping for a v2 control definition."""

    model_config = ConfigDict(extra="forbid")

    framework: str = Field(..., min_length=2)
    reference_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=3)
    relevance: str = Field(..., min_length=3)

    @field_validator("framework", "reference_id", "title", "relevance")
    @classmethod
    def strip_text(cls, value: str) -> str:
        """Normalize text fields used by registry filters."""
        return value.strip()


class RemediationCodeDefinition(BaseModel):
    """Non-executing remediation snippet for a control definition."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(..., min_length=2)
    label: str = Field(..., min_length=3)
    snippet: str = Field(..., min_length=3)

    @field_validator("kind", "label", "snippet")
    @classmethod
    def strip_text(cls, value: str) -> str:
        """Normalize snippet metadata while preserving the snippet body."""
        return value.strip()


class RemediationDefinition(BaseModel):
    """Human and machine-oriented remediation guidance for a control."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(..., min_length=8)
    cost_tier: RemediationCostTier
    manual_steps: list[str] = Field(..., min_length=1)
    code: list[RemediationCodeDefinition] = Field(default_factory=list)

    @field_validator("manual_steps")
    @classmethod
    def strip_manual_steps(cls, values: list[str]) -> list[str]:
        """Trim empty manual steps."""
        return [value.strip() for value in values if value.strip()]


class ControlDefinition(BaseModel):
    """Metadata-rich, filterable CRIS-SME control definition."""

    model_config = ConfigDict(extra="forbid")

    control_id: str = Field(..., min_length=3)
    version: str = Field(..., min_length=3)
    title: str = Field(..., min_length=5)
    domain: FindingCategory
    severity: FindingSeverity
    provider_support: dict[str, str] = Field(..., min_length=1)
    resource_type: str = Field(..., min_length=3)
    resource_group: str = Field(..., min_length=3)
    description: str = Field(..., min_length=8)
    risk: str = Field(..., min_length=8)
    evidence_requirements: list[str] = Field(..., min_length=1)
    freshness_hours: int = Field(..., ge=1)
    confidence_penalties: list[str] = Field(default_factory=list)
    compliance_mappings: list[ComplianceMappingDefinition] = Field(..., min_length=1)
    remediation: RemediationDefinition
    related_controls: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    assurance_claims: list[str] = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "evidence_requirements",
        "confidence_penalties",
        "related_controls",
        "dependencies",
        "assurance_claims",
    )
    @classmethod
    def strip_string_lists(cls, values: list[str]) -> list[str]:
        """Normalize list fields by trimming whitespace and dropping empty items."""
        return [value.strip() for value in values if value.strip()]

    @field_validator("provider_support")
    @classmethod
    def normalize_provider_support(cls, values: dict[str, str]) -> dict[str, str]:
        """Normalize provider names and validate support status values."""
        normalized: dict[str, str] = {}
        for provider, status in values.items():
            provider_key = provider.strip().lower()
            status_value = status.strip().lower()
            if status_value not in SUPPORTED_PROVIDER_STATUSES:
                raise ValueError(
                    f"Unsupported provider support status '{status}' for '{provider}'."
                )
            if provider_key:
                normalized[provider_key] = status_value
        if not normalized:
            raise ValueError("At least one provider support entry is required.")
        return normalized

    @model_validator(mode="after")
    def validate_unique_lists(self) -> "ControlDefinition":
        """Require list values that are used as registry keys to be unique."""
        for field_name in (
            "evidence_requirements",
            "confidence_penalties",
            "related_controls",
            "dependencies",
            "assurance_claims",
        ):
            values = getattr(self, field_name)
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} contains duplicate entries.")
        return self

    @property
    def frameworks(self) -> set[str]:
        """Return the framework names this control maps to."""
        return {mapping.framework for mapping in self.compliance_mappings}

    def supports_provider(
        self,
        provider: str,
        *,
        statuses: set[str] | None = None,
    ) -> bool:
        """Return whether the control has support for a provider/status filter."""
        normalized_provider = provider.strip().lower()
        support_status = self.provider_support.get(normalized_provider)
        if support_status is None:
            return False
        if statuses is None:
            return support_status != "unsupported"
        normalized_statuses = {status.strip().lower() for status in statuses}
        return support_status in normalized_statuses


@lru_cache(maxsize=1)
def load_control_definitions(
    path: str | Path = DEFAULT_CONTROL_METADATA_V2_PATH,
) -> dict[str, ControlDefinition]:
    """Load v2 control definitions as a control-id keyed mapping."""
    metadata_path = Path(path)
    raw_definitions = json.loads(metadata_path.read_text(encoding="utf-8"))
    definitions = [
        ControlDefinition.model_validate(item) for item in raw_definitions
    ]
    _validate_unique_control_ids(definitions)
    return {definition.control_id: definition for definition in definitions}


def get_control_definition(control_id: str) -> ControlDefinition:
    """Return one v2 control definition or raise a descriptive error."""
    definition = load_control_definitions().get(control_id)
    if definition is None:
        raise KeyError(f"Control definition '{control_id}' is missing from metadata v2.")
    return definition


def _validate_unique_control_ids(definitions: list[ControlDefinition]) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for definition in definitions:
        if definition.control_id in seen:
            duplicates.add(definition.control_id)
        seen.add(definition.control_id)
    if duplicates:
        duplicate_list = ", ".join(sorted(duplicates))
        raise ValueError(f"Duplicate control metadata v2 IDs: {duplicate_list}")
