"""Cross-check published registry metadata against canonical catalog and specs."""

from cris_sme.controls.catalog import load_control_catalog
from cris_sme.controls.definitions import ControlDefinition, validate_control_links
from cris_sme.policies.control_specs import load_control_specs


def validate_control_pack(definitions: dict[str, ControlDefinition]) -> None:
    catalog = load_control_catalog()
    missing = sorted(catalog.keys() - definitions.keys())
    extra = sorted(definitions.keys() - catalog.keys())
    if missing or extra:
        raise ValueError(f"Control catalog/metadata mismatch: missing={missing}, extra={extra}")
    validate_control_links(definitions)
    specs = load_control_specs()
    for key, definition in definitions.items():
        entry = catalog[key]
        fields = {
            "title": (definition.title, entry.title),
            "domain": (definition.domain, entry.category),
            "remediation summary": (definition.remediation.summary, entry.remediation_summary),
            "remediation cost": (definition.remediation.cost_tier, entry.remediation_cost_tier),
            "provider support": (definition.provider_support, specs[key].provider_support),
            "source mappings": (definition.metadata.get("source_mappings"), entry.mapping),
        }
        for name, (actual, expected) in fields.items():
            if actual != expected:
                raise ValueError(f"{key}: {name} differs from catalog/spec")
        for name in ("owner", "evaluator", "evaluator_function", "mapping_review_status",
                     "severity_basis", "freshness_basis", "assurance_claims_basis"):
            if not str(definition.metadata.get(name, "")).strip():
                raise ValueError(f"{key}: missing metadata {name}")
