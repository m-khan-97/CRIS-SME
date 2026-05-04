# Structured assurance case generation for CRIS-SME assessment artifacts.
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cris_sme.models.platform import AssuranceCase, AssuranceCaseArgument


def build_assurance_case(report: dict[str, Any]) -> AssuranceCase:
    """Build a structured argument that the assessment report is trustworthy."""
    claims = _claims_by_type(report)
    arguments = [
        _argument(
            key="report_replay_integrity",
            top_claim="This assessment is replayable and integrity-backed.",
            supporting_claims=[*claims.get("replay", []), *claims.get("integrity", [])],
            reasoning="Replay verifies deterministic reproduction while RBOM records report and artifact integrity.",
            required_types={"replay", "integrity"},
        ),
        _argument(
            key="risk_claims_traceable",
            top_claim="Risk conclusions are traceable to scored findings and evidence references.",
            supporting_claims=[*claims.get("overall_risk", []), *claims.get("top_risk", [])],
            reasoning="Overall and top-risk claims link to finding IDs, evidence references, and provenance nodes.",
            required_types={"overall_risk", "top_risk"},
        ),
        _argument(
            key="stakeholder_claims_caveated",
            top_claim="Executive, compliance, and insurance claims are explicitly verified or caveated.",
            supporting_claims=[
                *claims.get("trust_badge", []),
                *claims.get("cyber_essentials_readiness", []),
                *claims.get("cyber_essentials_pillar", []),
                *claims.get("insurance_question", []),
            ],
            reasoning="Stakeholder-facing claims preserve verification status, confidence, caveats, and mapped controls.",
            required_types={"trust_badge", "cyber_essentials_readiness", "insurance_question"},
        ),
        _evidence_quality_argument(report),
    ]
    assurance_score = _safe_float(
        _nested_dict(report, "assessment_assurance").get("assurance_score")
    )
    open_caveats = sorted({caveat for argument in arguments for caveat in argument.caveats})
    residual_gaps = sorted({gap for argument in arguments for gap in argument.residual_gaps})
    supported_count = sum(1 for argument in arguments if argument.conclusion == "supported")
    caveated_count = sum(1 for argument in arguments if argument.conclusion == "caveated")
    return AssuranceCase(
        generated_at=_string_or_none(report.get("generated_at")),
        overall_conclusion=_overall_conclusion(
            assurance_score=assurance_score,
            supported_count=supported_count,
            caveated_count=caveated_count,
            argument_count=len(arguments),
        ),
        assurance_score=round(assurance_score, 2),
        argument_count=len(arguments),
        supported_argument_count=supported_count,
        caveated_argument_count=caveated_count,
        arguments=arguments,
        open_caveats=open_caveats[:30],
        residual_gaps=residual_gaps[:30],
        deterministic_score_impact=(
            "No impact. The assurance case argues for report trustworthiness and never "
            "changes deterministic CRIS-SME risk scores."
        ),
    )


def write_assurance_case(
    assurance_case: AssuranceCase,
    output_path: str | Path,
) -> Path:
    """Write an assurance case JSON artifact."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(assurance_case.model_dump(mode="json"), indent=2), encoding="utf-8")
    return path


def _argument(
    *,
    key: str,
    top_claim: str,
    supporting_claims: list[dict[str, Any]],
    reasoning: str,
    required_types: set[str],
) -> AssuranceCaseArgument:
    present_types = {
        str(claim.get("claim_type"))
        for claim in supporting_claims
        if isinstance(claim, dict)
    }
    caveats = _claim_caveats(supporting_claims)
    residual_gaps: list[str] = []
    missing_types = sorted(required_types - present_types)
    if missing_types:
        residual_gaps.append(f"Missing supporting claim types: {', '.join(missing_types)}.")
    conclusion = _conclusion(
        has_required=not missing_types,
        caveats=caveats,
        supporting_claims=supporting_claims,
    )
    return AssuranceCaseArgument(
        argument_id=_argument_id(key),
        top_claim=top_claim,
        conclusion=conclusion,
        confidence=_argument_confidence(supporting_claims, missing_types, caveats),
        supporting_claim_ids=_claim_ids(supporting_claims),
        evidence_refs=_unique_list(
            ref
            for claim in supporting_claims
            for ref in claim.get("evidence_refs", [])
        )[:30],
        provenance_node_ids=_unique_list(
            node
            for claim in supporting_claims
            for node in claim.get("provenance_node_ids", [])
        )[:30],
        rbom_artifact_refs=_unique_list(
            artifact
            for claim in supporting_claims
            for artifact in claim.get("rbom_artifact_refs", [])
        )[:30],
        caveats=caveats[:20],
        residual_gaps=residual_gaps,
        reasoning=reasoning,
    )


def _evidence_quality_argument(report: dict[str, Any]) -> AssuranceCaseArgument:
    assurance = _nested_dict(report, "assessment_assurance")
    backlog = _nested_dict(report, "evidence_gap_backlog")
    high_priority_gaps = int(backlog.get("high_priority_count", 0))
    gaps = [
        str(item)
        for item in assurance.get("gaps", [])
        if str(item).strip()
    ]
    if high_priority_gaps:
        gaps.append(f"{high_priority_gaps} high-priority evidence gaps remain.")
    conclusion = "supported" if not gaps else "caveated"
    return AssuranceCaseArgument(
        argument_id=_argument_id("evidence_quality"),
        top_claim="Evidence quality and assurance gaps are explicit.",
        conclusion=conclusion,
        confidence=max(0.0, min(_safe_float(assurance.get("assurance_score")) / 100.0, 1.0)),
        supporting_claim_ids=[],
        evidence_refs=[],
        provenance_node_ids=["assurance:assessment", "snapshot:" + _snapshot_id(report)],
        rbom_artifact_refs=["json_report", "claim_verification_pack"],
        caveats=gaps[:20],
        residual_gaps=gaps[:20],
        reasoning="Assessment Assurance and Evidence Gap Backlog expose residual evidence-quality limitations.",
    )


def _claims_by_type(report: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    pack = report.get("claim_verification_pack", {})
    if not isinstance(pack, dict):
        return {}
    raw_claims = pack.get("claims", [])
    grouped: dict[str, list[dict[str, Any]]] = {}
    if isinstance(raw_claims, list):
        for claim in raw_claims:
            if not isinstance(claim, dict):
                continue
            grouped.setdefault(str(claim.get("claim_type", "unknown")), []).append(claim)
    return grouped


def _conclusion(
    *,
    has_required: bool,
    caveats: list[str],
    supporting_claims: list[dict[str, Any]],
) -> str:
    if not supporting_claims or not has_required:
        return "unsupported"
    if caveats or any(claim.get("verification_status") != "verified" for claim in supporting_claims):
        return "caveated"
    return "supported"


def _argument_confidence(
    supporting_claims: list[dict[str, Any]],
    missing_types: list[str],
    caveats: list[str],
) -> float:
    if not supporting_claims:
        return 0.0
    average = sum(_safe_float(claim.get("confidence")) for claim in supporting_claims) / len(supporting_claims)
    penalty = (0.15 * len(missing_types)) + (0.05 if caveats else 0.0)
    return round(max(0.0, min(average - penalty, 1.0)), 4)


def _overall_conclusion(
    *,
    assurance_score: float,
    supported_count: int,
    caveated_count: int,
    argument_count: int,
) -> str:
    if argument_count == 0:
        return "unsupported"
    if assurance_score >= 85 and supported_count >= argument_count - 1:
        return "supported"
    if supported_count + caveated_count == argument_count:
        return "caveated"
    return "limited"


def _claim_ids(claims: list[dict[str, Any]]) -> list[str]:
    return [
        str(claim.get("claim_id"))
        for claim in claims
        if str(claim.get("claim_id", "")).strip()
    ]


def _claim_caveats(claims: list[dict[str, Any]]) -> list[str]:
    return _unique_list(
        str(caveat)
        for claim in claims
        for caveat in claim.get("caveats", [])
        if str(caveat).strip()
    )


def _unique_list(items: Any) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        unique.append(text)
    return unique


def _snapshot_id(report: dict[str, Any]) -> str:
    snapshot = report.get("evidence_snapshot", {})
    if isinstance(snapshot, dict):
        return str(snapshot.get("snapshot_id", "snapshot_current"))
    return "snapshot_current"


def _nested_dict(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def _argument_id(key: str) -> str:
    return f"case_{hashlib.sha256(key.encode('utf-8')).hexdigest()[:14]}"


def _safe_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
