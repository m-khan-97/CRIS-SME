# Registry and filtering helpers for CRIS-SME control metadata v2.
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel, Field

from cris_sme.controls.definitions import (
    ControlDefinition,
    load_control_definitions,
    validate_control_links,
)
from cris_sme.models.finding import FindingCategory, FindingSeverity


class ControlRegistryFilter(BaseModel):
    """Filter criteria for selecting v2 control definitions."""

    control_ids: set[str] | None = None
    domains: set[FindingCategory] | None = None
    severities: set[FindingSeverity] | None = None
    providers: set[str] | None = None
    provider_statuses: set[str] | None = None
    frameworks: set[str] | None = None
    resource_groups: set[str] | None = None
    evidence_requirements: set[str] | None = None
    assurance_claims: set[str] | None = None
    include_dependencies: bool = Field(default=False)


class ControlRegistry:
    """In-memory registry for metadata-rich CRIS-SME controls."""

    def __init__(self, definitions: dict[str, ControlDefinition]) -> None:
        validate_control_links(definitions)
        self._definitions = dict(sorted(definitions.items()))

    @classmethod
    def load(cls, path: str | Path | None = None) -> "ControlRegistry":
        """Load a registry from the default or provided metadata path."""
        definitions = (
            load_control_definitions()
            if path is None
            else load_control_definitions(str(path))
        )
        if path is None:
            from cris_sme.controls.validation import validate_control_pack

            validate_control_pack(definitions)
        return cls(definitions)

    def all(self) -> list[ControlDefinition]:
        """Return all registered controls in stable ID order."""
        return list(self._definitions.values())

    def get(self, control_id: str) -> ControlDefinition:
        """Return one registered control by ID."""
        try:
            return self._definitions[control_id]
        except KeyError as exc:
            raise KeyError(
                f"Control definition '{control_id}' is not registered."
            ) from exc

    def filter(
        self,
        *,
        control_ids: Iterable[str] | None = None,
        domains: Iterable[str | FindingCategory] | None = None,
        severities: Iterable[str | FindingSeverity] | None = None,
        providers: Iterable[str] | None = None,
        provider_statuses: Iterable[str] | None = None,
        frameworks: Iterable[str] | None = None,
        resource_groups: Iterable[str] | None = None,
        evidence_requirements: Iterable[str] | None = None,
        assurance_claims: Iterable[str] | None = None,
        include_dependencies: bool = False,
    ) -> list[ControlDefinition]:
        """Return controls matching all provided filter dimensions."""
        criteria = ControlRegistryFilter(
            control_ids=_normalize_strings(control_ids),
            domains=_normalize_domains(domains),
            severities=_normalize_severities(severities),
            providers=_normalize_strings(providers, lowercase=True),
            provider_statuses=_normalize_strings(provider_statuses, lowercase=True),
            frameworks=_normalize_strings(frameworks, lowercase=True),
            resource_groups=_normalize_strings(resource_groups, lowercase=True),
            evidence_requirements=_normalize_strings(
                evidence_requirements,
                lowercase=True,
            ),
            assurance_claims=_normalize_strings(assurance_claims, lowercase=True),
            include_dependencies=include_dependencies,
        )
        selected = [
            definition
            for definition in self._definitions.values()
            if self._matches(definition, criteria)
        ]
        if include_dependencies:
            selected = self._with_dependencies(selected)
        return selected

    def _matches(
        self,
        definition: ControlDefinition,
        criteria: ControlRegistryFilter,
    ) -> bool:
        if criteria.control_ids and definition.control_id not in criteria.control_ids:
            return False
        if criteria.domains and definition.domain not in criteria.domains:
            return False
        if criteria.severities and definition.severity not in criteria.severities:
            return False
        if criteria.providers and not any(
            definition.supports_provider(
                provider,
                statuses=criteria.provider_statuses,
            )
            for provider in criteria.providers
        ):
            return False
        if criteria.frameworks and not _has_any(
            (mapping.framework for mapping in definition.compliance_mappings),
            criteria.frameworks,
        ):
            return False
        if (
            criteria.resource_groups
            and definition.resource_group.lower() not in criteria.resource_groups
        ):
            return False
        if criteria.evidence_requirements and not _has_any(
            definition.evidence_requirements,
            criteria.evidence_requirements,
        ):
            return False
        if criteria.assurance_claims and not _has_any(
            definition.assurance_claims,
            criteria.assurance_claims,
        ):
            return False
        return True

    def _with_dependencies(
        self,
        definitions: list[ControlDefinition],
    ) -> list[ControlDefinition]:
        selected: dict[str, ControlDefinition] = {
            definition.control_id: definition for definition in definitions
        }
        queue = list(definitions)
        while queue:
            definition = queue.pop(0)
            for dependency_id in definition.dependencies:
                if dependency_id in selected:
                    continue
                dependency = self._definitions[dependency_id]
                selected[dependency.control_id] = dependency
                queue.append(dependency)
        return [selected[control_id] for control_id in sorted(selected)]


def load_control_registry(path: str | Path | None = None) -> ControlRegistry:
    """Load the default v2 control registry."""
    return ControlRegistry.load(path)


def _normalize_strings(
    values: Iterable[str] | None,
    *,
    lowercase: bool = False,
) -> set[str] | None:
    if values is None:
        return None
    normalized = {
        value.strip().lower() if lowercase else value.strip()
        for value in values
        if value.strip()
    }
    return normalized or None


def _normalize_domains(
    values: Iterable[str | FindingCategory] | None,
) -> set[FindingCategory] | None:
    if values is None:
        return None
    return {
        value if isinstance(value, FindingCategory) else FindingCategory(value)
        for value in values
    }


def _normalize_severities(
    values: Iterable[str | FindingSeverity] | None,
) -> set[FindingSeverity] | None:
    if values is None:
        return None
    return {
        value if isinstance(value, FindingSeverity) else FindingSeverity(value)
        for value in values
    }


def _has_any(values: Iterable[str], expected: set[str]) -> bool:
    normalized_values = {value.strip().lower() for value in values}
    return bool(normalized_values.intersection(expected))
