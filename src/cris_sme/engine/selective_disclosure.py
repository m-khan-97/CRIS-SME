# Selective disclosure package generation for stakeholder-safe evidence sharing.
from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cris_sme.models.platform import (
    DisclosureRedaction,
    DisclosureRoom,
    DisclosureWithheldItem,
    SelectiveDisclosurePackage,
)


DISCLOSURE_PROFILES: dict[str, dict[str, Any]] = {
    "executive": {
        "name": "Executive Summary",
        "audience": "board and leadership",
        "level": "summary",
        "audiences": {"executive", "assurance"},
        "claim_types": {"overall_risk", "trust_badge", "replay", "integrity"},
        "evidence_limit": 0,
        "path_limit": 2,
    },
    "customer": {
        "name": "Customer Assurance",
        "audience": "customer due diligence",
        "level": "redacted assurance",
        "audiences": {"executive", "assurance", "compliance"},
        "claim_types": {
            "overall_risk",
            "trust_badge",
            "replay",
            "integrity",
            "top_risk",
            "cyber_essentials_readiness",
            "cyber_essentials_pillar",
        },
        "evidence_limit": 10,
        "path_limit": 5,
    },
    "insurer": {
        "name": "Insurance Readiness",
        "audience": "cyber insurance review",
        "level": "insurance evidence",
        "audiences": {"insurance", "assurance", "compliance", "executive"},
        "claim_types": {
            "overall_risk",
            "trust_badge",
            "replay",
            "integrity",
            "insurance_question",
            "cyber_essentials_readiness",
        },
        "evidence_limit": 12,
        "path_limit": 4,
    },
    "auditor": {
        "name": "Auditor Review",
        "audience": "external audit and assurance",
        "level": "redacted detailed evidence",
        "audiences": {"executive", "assurance", "compliance", "insurance"},
        "claim_types": {"*"},
        "evidence_limit": 25,
        "path_limit": 10,
    },
    "technical_appendix": {
        "name": "Technical Appendix",
        "audience": "technical reviewer",
        "level": "maximum redacted detail",
        "audiences": {"executive", "assurance", "compliance", "insurance"},
        "claim_types": {"*"},
        "evidence_limit": 40,
        "path_limit": 15,
    },
}

_SENSITIVE_KEYS = {
    "asset_id",
    "display_name",
    "email",
    "id",
    "name",
    "object_id",
    "organization",
    "organization_id",
    "organization_name",
    "principal_id",
    "principal_name",
    "resource_group",
    "resource_id",
    "resource_scope",
    "scope",
    "source_ref",
    "subscription_display_name",
    "subscription_id",
    "tenant_id",
    "tenant_scope",
    "upn",
    "user_principal_name",
}
_UUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_SUBSCRIPTION_PATH_RE = re.compile(r"/subscriptions/[^/\s]+(?:/[^,\s)]*)?", re.IGNORECASE)


def build_selective_disclosure_package(report: dict[str, Any]) -> SelectiveDisclosurePackage:
    """Build stakeholder-specific, redacted evidence-room views from deterministic artifacts."""
    rooms = [_build_room(profile_id, config, report) for profile_id, config in DISCLOSURE_PROFILES.items()]
    manifest = _build_share_manifest(report, rooms)
    return SelectiveDisclosurePackage(
        generated_at=_string_or_none(report.get("generated_at")) or _utc_now(),
        profile_count=len(rooms),
        rooms=rooms,
        share_manifest=manifest,
        guardrails=[
            "Disclosure profiles only select from existing CRIS-SME claims, evidence summaries, provenance paths, and assurance artifacts.",
            "Sensitive identifiers are redacted while preserving proof strength, counts, control IDs, finding IDs, and verification status.",
            "Withheld evidence is explicitly recorded with a reason and replacement summary.",
            "Selective disclosure never changes deterministic CRIS-SME risk scores.",
        ],
        deterministic_score_impact=(
            "No impact. The evidence room controls stakeholder disclosure and never changes "
            "deterministic CRIS-SME findings, claims, or scores."
        ),
    )


def write_selective_disclosure_package(
    package: SelectiveDisclosurePackage,
    output_path: str | Path,
) -> Path:
    """Write the Selective Disclosure Evidence Room package JSON artifact."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(package.model_dump(mode="json"), indent=2), encoding="utf-8")
    return path


def _build_room(profile_id: str, config: dict[str, Any], report: dict[str, Any]) -> DisclosureRoom:
    claims, claim_redactions = _claims_for_profile(config, report)
    evidence, evidence_redactions, withheld = _evidence_for_profile(profile_id, config, report)
    assurance_case, assurance_redactions = _assurance_case_for_profile(config, report)
    narrative, narrative_redactions = _narrative_for_claims(claims, report)
    paths, path_redactions = _paths_for_profile(config, report)
    redactions = [
        *claim_redactions,
        *evidence_redactions,
        *assurance_redactions,
        *narrative_redactions,
        *path_redactions,
    ]
    room_body = {
        "profile_id": profile_id,
        "claims": claims,
        "assurance_case": assurance_case,
        "claim_bound_narrative": narrative,
        "provenance_paths": paths,
        "shared_evidence": evidence,
        "withheld_items": [item.model_dump(mode="json") for item in withheld],
    }
    return DisclosureRoom(
        profile_id=profile_id,
        profile_name=str(config["name"]),
        audience=str(config["audience"]),
        disclosure_level=str(config["level"]),
        included_sections=_included_sections(profile_id, evidence),
        included_claim_count=len(claims),
        shared_evidence_count=len(evidence),
        redaction_count=len(redactions),
        withheld_count=len(withheld),
        claims=claims,
        assurance_case=assurance_case,
        claim_bound_narrative=narrative,
        provenance_paths=paths,
        shared_evidence=evidence,
        withheld_items=withheld,
        redactions=redactions,
        integrity={
            "room_sha256": _sha256_json(room_body),
            "rbom_report_sha256": str(
                _dict(report.get("risk_bill_of_materials")).get("canonical_report_sha256", "unavailable")
            ),
        },
        deterministic_score_impact="No impact. This room is a redacted view over existing report artifacts.",
    )


def _claims_for_profile(config: dict[str, Any], report: dict[str, Any]) -> tuple[list[dict[str, Any]], list[DisclosureRedaction]]:
    allowed_audiences = set(config.get("audiences", set()))
    allowed_types = set(config.get("claim_types", set()))
    selected: list[dict[str, Any]] = []
    redactions: list[DisclosureRedaction] = []
    for claim in _list(_dict(report.get("claim_verification_pack")).get("claims")):
        if not isinstance(claim, dict):
            continue
        claim_type = str(claim.get("claim_type", ""))
        audience = str(claim.get("audience", ""))
        if "*" not in allowed_types and claim_type not in allowed_types and audience not in allowed_audiences:
            continue
        cleaned = {
            "claim_id": claim.get("claim_id"),
            "claim_type": claim_type,
            "audience": audience,
            "statement": claim.get("statement"),
            "verification_status": claim.get("verification_status"),
            "confidence": claim.get("confidence"),
            "control_ids": claim.get("control_ids", []),
            "finding_ids": claim.get("finding_ids", []),
            "provenance_node_ids": claim.get("provenance_node_ids", []),
            "rbom_artifact_refs": claim.get("rbom_artifact_refs", []),
            "caveats": claim.get("caveats", []),
            "deterministic_score_impact": claim.get("deterministic_score_impact"),
        }
        redacted, events = _redact(cleaned, f"claims.{claim.get('claim_id', 'unknown')}")
        selected.append(redacted)
        redactions.extend(events)
    return selected, redactions


def _evidence_for_profile(
    profile_id: str,
    config: dict[str, Any],
    report: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[DisclosureRedaction], list[DisclosureWithheldItem]]:
    limit = int(config.get("evidence_limit", 0))
    risks = [item for item in _list(report.get("prioritized_risks")) if isinstance(item, dict)]
    shared: list[dict[str, Any]] = []
    redactions: list[DisclosureRedaction] = []
    withheld: list[DisclosureWithheldItem] = []
    if limit == 0:
        withheld.extend(
            DisclosureWithheldItem(
                item_id=_stable_id("withheld", profile_id, str(risk.get("finding_id", index))),
                source_section="prioritized_risks.evidence",
                reason="This disclosure profile is summary-only and does not share finding-level evidence.",
                replacement_summary=(
                    f"{risk.get('control_id', 'control')} evidence summarized by verified claims, scores, caveats, and assurance case."
                ),
            )
            for index, risk in enumerate(risks[:8])
        )
        return shared, redactions, withheld
    for risk in risks:
        evidence_refs = [str(item) for item in _list(risk.get("evidence")) if str(item).strip()]
        if not evidence_refs:
            continue
        if len(shared) < limit:
            item = {
                "finding_id": risk.get("finding_id"),
                "control_id": risk.get("control_id"),
                "title": risk.get("title"),
                "priority": risk.get("priority"),
                "score": risk.get("score"),
                "resource_scope": risk.get("resource_scope"),
                "evidence": evidence_refs,
                "evidence_quality": risk.get("evidence_quality", {}),
                "proof_strength": _proof_strength(risk),
            }
            redacted, events = _redact(item, f"shared_evidence.{risk.get('finding_id', 'unknown')}")
            shared.append(redacted)
            redactions.extend(events)
        else:
            withheld.append(
                DisclosureWithheldItem(
                    item_id=_stable_id("withheld", profile_id, str(risk.get("finding_id", "unknown"))),
                    source_section="prioritized_risks.evidence",
                    reason="Profile evidence limit reached; detailed evidence is available in a more privileged disclosure profile.",
                    replacement_summary=(
                        f"{risk.get('control_id', 'control')} evidence withheld; "
                        f"{len(evidence_refs)} supporting evidence statement(s) remain verifiable in internal artifacts."
                    ),
                )
            )
    return shared, redactions, withheld


def _assurance_case_for_profile(config: dict[str, Any], report: dict[str, Any]) -> tuple[dict[str, Any], list[DisclosureRedaction]]:
    case = _dict(report.get("assurance_case"))
    arguments = [item for item in _list(case.get("arguments")) if isinstance(item, dict)]
    if str(config.get("level")) == "summary":
        arguments = arguments[:2]
    cleaned = {
        "case_name": case.get("case_name"),
        "overall_conclusion": case.get("overall_conclusion"),
        "assurance_score": case.get("assurance_score"),
        "argument_count": len(arguments),
        "arguments": arguments,
        "open_caveats": case.get("open_caveats", [])[:10],
        "residual_gaps": case.get("residual_gaps", [])[:10],
        "deterministic_score_impact": case.get("deterministic_score_impact"),
    }
    return _redact(cleaned, "assurance_case")


def _narrative_for_claims(claims: list[dict[str, Any]], report: dict[str, Any]) -> tuple[dict[str, Any], list[DisclosureRedaction]]:
    allowed_claim_ids = {str(claim.get("claim_id")) for claim in claims}
    narrative = _dict(report.get("claim_bound_narrative"))
    sections = []
    for section in _list(narrative.get("sections")):
        if not isinstance(section, dict):
            continue
        cited = {str(item) for item in _list(section.get("cited_claim_ids"))}
        if cited & allowed_claim_ids:
            sections.append(section)
    cleaned = {
        "section_count": len(sections),
        "cited_claim_count": len({claim for section in sections for claim in _list(section.get("cited_claim_ids"))}),
        "sections": sections,
        "guardrails": narrative.get("guardrails", []),
    }
    return _redact(cleaned, "claim_bound_narrative")


def _paths_for_profile(config: dict[str, Any], report: dict[str, Any]) -> tuple[list[dict[str, Any]], list[DisclosureRedaction]]:
    limit = int(config.get("path_limit", 0))
    paths = [
        {
            "control_id": path.get("control_id"),
            "finding_id": path.get("finding_id"),
            "summary": path.get("summary"),
            "node_ids": path.get("node_ids", []),
        }
        for path in _list(_dict(report.get("decision_provenance_graph")).get("top_decision_paths"))[:limit]
        if isinstance(path, dict)
    ]
    return _redact(paths, "provenance_paths")


def _build_share_manifest(report: dict[str, Any], rooms: list[DisclosureRoom]) -> dict[str, Any]:
    artifacts = _dict(report.get("report_artifacts"))
    included_artifacts = {
        key: value
        for key, value in artifacts.items()
        if key
        in {
            "assurance_case",
            "assurance_portal",
            "claim_bound_narrative",
            "claim_verification_pack",
            "decision_provenance_graph",
            "risk_bill_of_materials",
        }
    }
    return {
        "manifest_schema_version": "1.0.0",
        "generated_at": _string_or_none(report.get("generated_at")) or _utc_now(),
        "disclosure_profiles": [
            {
                "profile_id": room.profile_id,
                "profile_name": room.profile_name,
                "audience": room.audience,
                "disclosure_level": room.disclosure_level,
                "included_claim_count": room.included_claim_count,
                "shared_evidence_count": room.shared_evidence_count,
                "redaction_count": room.redaction_count,
                "withheld_count": room.withheld_count,
                "room_sha256": room.integrity.get("room_sha256"),
            }
            for room in rooms
        ],
        "included_artifacts": included_artifacts,
        "withheld_artifact_classes": [
            {
                "artifact_class": "raw_cloud_inventory",
                "reason": "Raw collector inventory may contain tenant, subscription, user, resource, network, and workload identifiers.",
            },
            {
                "artifact_class": "unredacted_resource_scope",
                "reason": "Resource scopes are replaced with redacted summaries in shared evidence views.",
            },
        ],
        "rbom_report_sha256": str(
            _dict(report.get("risk_bill_of_materials")).get("canonical_report_sha256", "unavailable")
        ),
    }


def _redact(value: Any, path: str) -> tuple[Any, list[DisclosureRedaction]]:
    events: list[DisclosureRedaction] = []

    def walk(item: Any, field_path: str) -> Any:
        if isinstance(item, dict):
            output: dict[str, Any] = {}
            for key, child in item.items():
                key_text = str(key)
                child_path = f"{field_path}.{key_text}" if field_path else key_text
                if key_text.lower() in _SENSITIVE_KEYS and child not in (None, "", [], {}):
                    output[key_text] = _redaction_token(key_text, child)
                    events.append(_redaction_event(child_path, "sensitive_field"))
                else:
                    output[key_text] = walk(child, child_path)
            return output
        if isinstance(item, list):
            return [walk(child, f"{field_path}[{index}]") for index, child in enumerate(item)]
        if isinstance(item, str):
            return _redact_string(item, field_path, events)
        return deepcopy(item)

    return walk(value, path), events


def _redact_string(value: str, field_path: str, events: list[DisclosureRedaction]) -> str:
    redacted = value
    for pattern, token, redaction_type in [
        (_SUBSCRIPTION_PATH_RE, "[redacted-resource-path]", "resource_path"),
        (_EMAIL_RE, "[redacted-email]", "email"),
        (_UUID_RE, "[redacted-id]", "identifier"),
        (_IP_RE, "[redacted-ip]", "network_address"),
    ]:
        redacted, count = pattern.subn(token, redacted)
        if count:
            events.append(_redaction_event(field_path, redaction_type))
    return redacted


def _redaction_token(key: str, value: Any) -> str:
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:10]
    return f"[redacted-{key}:{digest}]"


def _redaction_event(field_path: str, redaction_type: str) -> DisclosureRedaction:
    return DisclosureRedaction(
        redaction_id=_stable_id("redaction", field_path, redaction_type),
        field_path=field_path,
        redaction_type=redaction_type,
        reason="Sensitive tenant, resource, identity, or network detail withheld from shared evidence.",
    )


def _included_sections(profile_id: str, evidence: list[dict[str, Any]]) -> list[str]:
    sections = [
        "share_manifest",
        "claim_verification_pack",
        "assurance_case",
        "claim_bound_narrative",
        "decision_provenance_paths",
        "rbom_integrity_reference",
    ]
    if evidence:
        sections.append("redacted_finding_evidence")
    if profile_id in {"insurer", "auditor", "technical_appendix"}:
        sections.append("withheld_evidence_register")
    return sections


def _proof_strength(risk: dict[str, Any]) -> str:
    quality = _dict(risk.get("evidence_quality"))
    sufficiency = str(quality.get("sufficiency", "unknown"))
    direct_count = int(quality.get("direct_evidence_count", 0) or 0)
    if sufficiency == "sufficient" and direct_count > 0:
        return "direct"
    if sufficiency in {"partial", "inferred"}:
        return "caveated"
    return "limited"


def _sha256_json(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _stable_id(*parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:14]
    return f"dscl_{digest}"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
