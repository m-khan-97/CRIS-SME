# Claim verification pack generation for stakeholder-facing CRIS-SME statements.
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cris_sme.models.platform import ClaimVerification, ClaimVerificationPack


def build_claim_verification_pack(report: dict[str, Any]) -> ClaimVerificationPack:
    """Build verifiable claims from executive, insurance, readiness, and assurance outputs."""
    claims = [
        _overall_risk_claim(report),
        _replay_claim(report),
        _rbom_claim(report),
        _trust_badge_claim(report),
        *_top_risk_claims(report),
        *_cyber_essentials_claims(report),
        *_insurance_claims(report),
    ]
    claims = [claim for claim in claims if claim is not None]
    return ClaimVerificationPack(
        generated_at=_string_or_none(report.get("generated_at")),
        claim_count=len(claims),
        verified_claim_count=sum(1 for claim in claims if claim.verification_status == "verified"),
        caveated_claim_count=sum(1 for claim in claims if claim.caveats),
        claim_type_counts=_claim_type_counts(claims),
        claims=claims,
    )


def write_claim_verification_pack(
    pack: ClaimVerificationPack,
    output_path: str | Path,
) -> Path:
    """Write a Claim Verification Pack JSON artifact."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pack.model_dump(mode="json"), indent=2), encoding="utf-8")
    return path


def _overall_risk_claim(report: dict[str, Any]) -> ClaimVerification:
    score = _safe_float(report.get("overall_risk_score"))
    return ClaimVerification(
        claim_id=_claim_id("overall_risk", str(score)),
        claim_type="overall_risk",
        audience="executive",
        statement=f"Overall CRIS-SME risk score is {score:.2f}/100.",
        verification_status="verified",
        confidence=0.95,
        source_sections=["summary", "overall_risk_score", "category_scores"],
        evidence_refs=_all_evidence_refs(report)[:20],
        control_ids=_control_ids(report),
        finding_ids=_finding_ids(report)[:30],
        provenance_node_ids=["snapshot:" + _snapshot_id(report), "assurance:assessment"],
        rbom_artifact_refs=["json_report"],
        caveats=_global_caveats(report),
        deterministic_score_impact="No impact. Claim verification records report statements and never changes deterministic risk scores.",
    )


def _replay_claim(report: dict[str, Any]) -> ClaimVerification:
    replay = _nested_dict(report, "assessment_replay", "replay")
    verified = bool(replay.get("deterministic_match"))
    return ClaimVerification(
        claim_id=_claim_id("replay", str(replay.get("snapshot_id", "unknown"))),
        claim_type="replay",
        audience="assurance",
        statement=(
            "Assessment replay reproduced deterministic findings and risk scores."
            if verified
            else "Assessment replay is not verified for this report."
        ),
        verification_status="verified" if verified else "caveated",
        confidence=1.0 if verified else 0.35,
        source_sections=["assessment_replay", "evidence_snapshot"],
        evidence_refs=[],
        control_ids=[],
        finding_ids=[],
        provenance_node_ids=["replay:assessment", "snapshot:" + _snapshot_id(report)],
        rbom_artifact_refs=["evidence_snapshot"],
        caveats=[] if verified else ["Deterministic replay did not verify cleanly."],
        deterministic_score_impact="No impact. Replay verifies deterministic scoring but does not alter it.",
    )


def _rbom_claim(report: dict[str, Any]) -> ClaimVerification:
    rbom = report.get("risk_bill_of_materials")
    present = isinstance(rbom, dict) and bool(rbom.get("canonical_report_sha256"))
    return ClaimVerification(
        claim_id=_claim_id("rbom", str(rbom.get("canonical_report_sha256", "missing")) if isinstance(rbom, dict) else "missing"),
        claim_type="integrity",
        audience="assurance",
        statement=(
            "Report includes a Risk Bill of Materials integrity manifest."
            if present
            else "Report does not include a complete Risk Bill of Materials integrity manifest."
        ),
        verification_status="verified" if present else "unverified",
        confidence=1.0 if present else 0.0,
        source_sections=["risk_bill_of_materials", "report_artifacts"],
        evidence_refs=[],
        control_ids=[],
        finding_ids=[],
        provenance_node_ids=["rbom:assessment"],
        rbom_artifact_refs=["risk_bill_of_materials"],
        caveats=[] if present else ["RBOM is missing or incomplete."],
        deterministic_score_impact="No impact. RBOM verifies artifact integrity and never changes risk scoring.",
    )


def _trust_badge_claim(report: dict[str, Any]) -> ClaimVerification | None:
    badge = report.get("report_trust_badge")
    if not isinstance(badge, dict):
        return None
    caveats = [str(item) for item in badge.get("caveats", []) if str(item).strip()]
    return ClaimVerification(
        claim_id=_claim_id("trust_badge", str(badge.get("level", "unknown"))),
        claim_type="trust_badge",
        audience="executive",
        statement=str(badge.get("statement", "Report trust badge is available.")),
        verification_status="verified" if not caveats else "caveated",
        confidence=_safe_float(badge.get("assurance_score")) / 100.0,
        source_sections=["report_trust_badge", "assessment_assurance"],
        evidence_refs=[],
        control_ids=[],
        finding_ids=[],
        provenance_node_ids=["trust_badge:report", "assurance:assessment"],
        rbom_artifact_refs=["json_report"],
        caveats=caveats,
        deterministic_score_impact=str(badge.get("risk_score_impact", "No impact on deterministic risk scores.")),
    )


def _top_risk_claims(report: dict[str, Any]) -> list[ClaimVerification]:
    claims: list[ClaimVerification] = []
    for risk in _risks(report)[:5]:
        finding_id = str(risk.get("finding_id", "unknown"))
        control_id = str(risk.get("control_id", "unknown"))
        quality = risk.get("evidence_quality", {})
        sufficiency = str(quality.get("sufficiency", "unknown")) if isinstance(quality, dict) else "unknown"
        caveats = []
        if sufficiency != "sufficient":
            caveats.append(f"Evidence sufficiency is {sufficiency}.")
        claims.append(
            ClaimVerification(
                claim_id=_claim_id("top_risk", finding_id),
                claim_type="top_risk",
                audience="executive",
                statement=(
                    f"{control_id} is a {risk.get('priority', 'priority')} risk "
                    f"with score {_safe_float(risk.get('score')):.2f}."
                ),
                verification_status="verified" if not caveats else "caveated",
                confidence=_risk_confidence(risk),
                source_sections=["prioritized_risks", "decision_provenance_graph"],
                evidence_refs=_finding_evidence_refs(risk),
                control_ids=[control_id],
                finding_ids=[finding_id],
                provenance_node_ids=[
                    f"finding:{finding_id}",
                    f"score:{finding_id}",
                    f"evidence_sufficiency:{finding_id}",
                ],
                rbom_artifact_refs=["json_report", "decision_provenance_graph"],
                caveats=caveats,
                deterministic_score_impact="No impact. This claim describes an already-scored finding.",
            )
        )
    return claims


def _cyber_essentials_claims(report: dict[str, Any]) -> list[ClaimVerification]:
    readiness = report.get("cyber_essentials_readiness")
    if not isinstance(readiness, dict):
        return []
    claims = [
        ClaimVerification(
            claim_id=_claim_id("cyber_essentials", "overall"),
            claim_type="cyber_essentials_readiness",
            audience="compliance",
            statement=f"Cyber Essentials readiness score is {_safe_float(readiness.get('overall_readiness_score')):.2f}/100.",
            verification_status="verified",
            confidence=0.85,
            source_sections=["cyber_essentials_readiness"],
            evidence_refs=[],
            control_ids=_controls_from_pillars(readiness),
            finding_ids=[],
            provenance_node_ids=["snapshot:" + _snapshot_id(report)],
            rbom_artifact_refs=["json_report"],
            caveats=_global_caveats(report),
            deterministic_score_impact="No impact. Readiness claims summarize mapped controls without changing risk scores.",
        )
    ]
    for pillar in readiness.get("pillars", []):
        if not isinstance(pillar, dict):
            continue
        active_controls = [str(item) for item in pillar.get("active_control_ids", [])]
        status = str(pillar.get("status", "unknown"))
        claims.append(
            ClaimVerification(
                claim_id=_claim_id("cyber_essentials_pillar", str(pillar.get("pillar_id", "pillar"))),
                claim_type="cyber_essentials_pillar",
                audience="compliance",
                statement=f"{pillar.get('pillar_name', 'Pillar')} readiness is {status}.",
                verification_status="verified" if status == "ready" else "caveated",
                confidence=0.85 if status == "ready" else 0.7,
                source_sections=["cyber_essentials_readiness"],
                evidence_refs=[],
                control_ids=active_controls,
                finding_ids=_finding_ids_for_controls(report, active_controls),
                provenance_node_ids=[f"control:{control_id}" for control_id in active_controls],
                rbom_artifact_refs=["json_report"],
                caveats=[] if status == "ready" else [f"Active mapped controls: {', '.join(active_controls) or 'none recorded'}."],
                deterministic_score_impact="No impact. Pillar claims summarize mapped controls without changing scores.",
            )
        )
    return claims


def _insurance_claims(report: dict[str, Any]) -> list[ClaimVerification]:
    insurance = report.get("cyber_insurance_evidence")
    if not isinstance(insurance, dict):
        return []
    claims: list[ClaimVerification] = []
    for question in insurance.get("questions", []):
        if not isinstance(question, dict):
            continue
        question_id = str(question.get("question_id", "INS-?"))
        status = str(question.get("status", "unknown"))
        controls = [str(item) for item in question.get("related_controls", [])]
        caveats = []
        if status != "met":
            caveats.append(str(question.get("recommended_next_step", "Review linked controls.")))
        claims.append(
            ClaimVerification(
                claim_id=_claim_id("insurance_question", question_id),
                claim_type="insurance_question",
                audience="insurance",
                statement=f"{question_id} status is {status}: {question.get('evidence_statement', '')}",
                verification_status="verified" if status == "met" else "caveated",
                confidence={"met": 0.85, "partial": 0.65, "not_met": 0.75}.get(status, 0.4),
                source_sections=["cyber_insurance_evidence"],
                evidence_refs=_evidence_refs_from_supporting_findings(question),
                control_ids=controls,
                finding_ids=_finding_ids_for_controls(report, controls),
                provenance_node_ids=[f"control:{control_id}" for control_id in controls],
                rbom_artifact_refs=["cyber_insurance_pack.cyber_insurance_json"],
                caveats=caveats,
                deterministic_score_impact="No impact. Insurance claims summarize mapped control evidence without changing scores.",
            )
        )
    return claims


def _risks(report: dict[str, Any]) -> list[dict[str, Any]]:
    risks = report.get("prioritized_risks", [])
    return [item for item in risks if isinstance(item, dict)] if isinstance(risks, list) else []


def _all_evidence_refs(report: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for risk in _risks(report):
        refs.extend(_finding_evidence_refs(risk))
    return sorted(set(refs))


def _finding_evidence_refs(risk: dict[str, Any]) -> list[str]:
    trace = risk.get("finding_trace")
    if isinstance(trace, dict):
        refs = trace.get("evidence_refs", [])
        if isinstance(refs, list):
            return [str(item) for item in refs if str(item).strip()]
    return []


def _evidence_refs_from_supporting_findings(question: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    findings = question.get("supporting_findings", [])
    if isinstance(findings, list):
        for finding in findings:
            if isinstance(finding, dict):
                refs.extend(str(item) for item in finding.get("evidence", [])[:2])
    return refs[:10]


def _control_ids(report: dict[str, Any]) -> list[str]:
    return sorted({str(risk.get("control_id")) for risk in _risks(report) if risk.get("control_id")})


def _finding_ids(report: dict[str, Any]) -> list[str]:
    return sorted({str(risk.get("finding_id")) for risk in _risks(report) if risk.get("finding_id")})


def _finding_ids_for_controls(report: dict[str, Any], control_ids: list[str]) -> list[str]:
    wanted = set(control_ids)
    return [
        str(risk.get("finding_id"))
        for risk in _risks(report)
        if str(risk.get("control_id")) in wanted and risk.get("finding_id")
    ]


def _controls_from_pillars(readiness: dict[str, Any]) -> list[str]:
    controls: set[str] = set()
    for pillar in readiness.get("pillars", []):
        if isinstance(pillar, dict):
            controls.update(str(item) for item in pillar.get("active_control_ids", []))
    return sorted(controls)


def _risk_confidence(risk: dict[str, Any]) -> float:
    calibration = risk.get("confidence_calibration", {})
    if isinstance(calibration, dict):
        return min(max(_safe_float(calibration.get("calibrated_confidence")), 0.0), 1.0)
    return 0.7


def _global_caveats(report: dict[str, Any]) -> list[str]:
    caveats: list[str] = []
    badge = report.get("report_trust_badge", {})
    if isinstance(badge, dict):
        caveats.extend(str(item) for item in badge.get("caveats", []) if str(item).strip())
    assurance = report.get("assessment_assurance", {})
    if isinstance(assurance, dict):
        caveats.extend(str(item) for item in assurance.get("gaps", [])[:3] if str(item).strip())
    return caveats


def _snapshot_id(report: dict[str, Any]) -> str:
    snapshot = report.get("evidence_snapshot", {})
    if isinstance(snapshot, dict):
        return str(snapshot.get("snapshot_id", "snapshot_current"))
    return "snapshot_current"


def _nested_dict(payload: dict[str, Any], *keys: str) -> dict[str, Any]:
    current: object = payload
    for key in keys:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return current if isinstance(current, dict) else {}


def _claim_type_counts(claims: list[ClaimVerification]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for claim in claims:
        counts[claim.claim_type] = counts.get(claim.claim_type, 0) + 1
    return counts


def _claim_id(*parts: str) -> str:
    raw = "|".join(parts)
    return f"clm_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:14]}"


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
