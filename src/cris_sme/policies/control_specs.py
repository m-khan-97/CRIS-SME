# Control-governance metadata for CRIS-SME controls.
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from cris_sme.controls.catalog import load_control_catalog


DEFAULT_CONTROL_SPEC_OVERRIDES_PATH = Path("data/control_spec_overrides.json")
POLICY_PACK_VERSION = "2026.04.0"


class ControlSpec(BaseModel):
    """Versioned declarative metadata describing how a control should be interpreted."""

    control_id: str = Field(..., min_length=3)
    version: str = Field(..., min_length=3)
    intent: str = Field(..., min_length=8)
    domain: str = Field(..., min_length=2)
    applicability: str = Field(..., min_length=3)
    evidence_requirements: list[str] = Field(default_factory=list)
    provider_support: dict[str, str] = Field(default_factory=dict)
    remediation_template: str = Field(..., min_length=8)
    exception_guidance: str = Field(..., min_length=8)
    known_limitations: list[str] = Field(default_factory=list)
    confidence_penalty_rules: list[str] = Field(default_factory=list)
    mapping: list[str] = Field(default_factory=list)


def load_control_specs(
    path: str | Path = DEFAULT_CONTROL_SPEC_OVERRIDES_PATH,
) -> dict[str, ControlSpec]:
    """Load a full control-spec catalog, using catalog-derived defaults plus overrides."""
    catalog = load_control_catalog()
    overrides = _load_overrides(path)
    specs: dict[str, ControlSpec] = {}

    for control_id, control in catalog.items():
        default_spec = {
            "control_id": control_id,
            "version": "1.0.0",
            "intent": control.title,
            "domain": control.category.value,
            "applicability": "azure_first_provider_neutral_core",
            "evidence_requirements": _default_evidence_requirements(control.category.value),
            "provider_support": {
                "azure": "active",
                "aws": "planned",
                "gcp": "planned",
            },
            "remediation_template": control.remediation_summary,
            "exception_guidance": (
                "Exceptions require compensating controls, a bounded expiry, and documented owner approval."
            ),
            "known_limitations": _default_limitations(control.control_id, control.category.value),
            "confidence_penalty_rules": _default_confidence_penalty_rules(control.control_id),
            "mapping": list(control.mapping),
        }
        merged = {**default_spec, **overrides.get(control_id, {})}
        specs[control_id] = ControlSpec.model_validate(merged)

    return specs


@lru_cache(maxsize=1)
def load_policy_pack_metadata() -> dict[str, Any]:
    """Return compact metadata describing the currently active control policy pack."""
    specs = load_control_specs()
    azure_active = sum(
        1
        for spec in specs.values()
        if str(spec.provider_support.get("azure", "")).lower() == "active"
    )
    return {
        "policy_pack_version": POLICY_PACK_VERSION,
        "controls_total": len(specs),
        "controls_with_provider_support": azure_active,
        "generated_from_catalog": True,
        "notes": (
            "Control policy metadata is generated from the control catalog with explicit "
            "overrides for known observability limitations and provider support posture."
        ),
    }


def get_control_spec(control_id: str) -> ControlSpec:
    """Return one control spec and raise a clear error if missing."""
    spec = load_control_specs().get(control_id)
    if spec is None:
        raise KeyError(f"Control spec for '{control_id}' is not defined.")
    return spec


def _load_overrides(path: str | Path) -> dict[str, dict[str, Any]]:
    override_path = Path(path)
    if not override_path.exists():
        return {}

    raw = json.loads(override_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        return {
            str(control_id): value
            for control_id, value in raw.items()
            if isinstance(value, dict)
        }
    return {}


def _default_evidence_requirements(domain: str) -> list[str]:
    normalized = domain.lower()
    if "iam" in normalized:
        return [
            "privileged assignment inventory",
            "identity governance visibility context",
        ]
    if "network" in normalized:
        return [
            "inbound exposure inventory",
            "administrative path restriction evidence",
        ]
    if "data" in normalized:
        return [
            "public data-path and encryption evidence",
            "backup/retention control-state evidence",
        ]
    if "monitoring" in normalized:
        return [
            "log retention and alerting evidence",
            "incident runbook or workflow evidence",
        ]
    if "compute" in normalized:
        return [
            "patch posture proxy evidence",
            "workload hardening and endpoint coverage evidence",
        ]
    return [
        "resource inventory evidence",
        "governance policy/budget/tagging control evidence",
    ]


def _default_confidence_penalty_rules(control_id: str) -> list[str]:
    if control_id == "IAM-005":
        return [
            "apply no penalty when observability finding is itself derived from direct scope signals",
        ]
    return [
        "reduce confidence when required evidence fields are unavailable",
        "reduce confidence when evidence is inferred from partial tenant scope",
    ]


def _default_limitations(control_id: str, domain: str) -> list[str]:
    if control_id.startswith("IAM"):
        return [
            "tenant-wide identity controls can be partially observable depending on Entra permissions",
        ]
    if control_id in {"CMP-001", "CMP-003", "GOV-004"}:
        return [
            "this control currently relies on conservative proxy or heuristic evidence paths",
        ]
    if "network" in domain.lower():
        return [
            "network exposure is assessed at visible scope and does not claim full attack-path simulation",
        ]
    return []
