# Cyber Essentials self-assessment pre-population from CRIS-SME evidence.
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_CE_QUESTION_MAPPING_PATH = Path("data/ce_question_mapping.json")

TERMINAL_STATUSES = {
    "endpoint_required",
    "policy_required",
    "manual_required",
    "insufficient_evidence",
}


def load_ce_question_mapping(path: str | Path | None = None) -> dict[str, Any]:
    """Load the paraphrased Cyber Essentials question mapping dataset."""
    mapping_path = Path(path) if path is not None else DEFAULT_CE_QUESTION_MAPPING_PATH
    return json.loads(mapping_path.read_text(encoding="utf-8"))


def build_ce_self_assessment_pack(
    report: dict[str, Any],
    *,
    mapping: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a CE answer pre-population pack from an existing CRIS-SME report."""
    question_mapping = mapping or load_ce_question_mapping()
    questions = [
        question
        for question in question_mapping.get("questions", [])
        if isinstance(question, dict)
    ]
    risks_by_control = _risks_by_control(report)
    answers = [
        _build_answer_entry(question, risks_by_control)
        for question in questions
    ]
    evidence_counts = Counter(str(answer["evidence_class"]) for answer in answers)
    status_counts = Counter(str(answer["proposed_status"]) for answer in answers)
    section_counts = Counter(str(answer["section"]) for answer in answers)
    technical_answers = [
        answer for answer in answers if answer.get("research_scope") == "technical_control"
    ]
    technical_counts = Counter(
        str(answer["evidence_class"]) for answer in technical_answers
    )

    return {
        "pack_schema_version": "0.1.0",
        "pack_name": "CRIS-SME Cyber Essentials Self-Assessment Pre-Population Pack",
        "deterministic_score_impact": "No impact. This pack reads existing CRIS-SME findings and never changes deterministic risk scores.",
        "certification_boundary": (
            "This artifact does not certify Cyber Essentials compliance. It pre-populates "
            "candidate answer statuses from available evidence for human review."
        ),
        "question_set": question_mapping.get("question_set", {}),
        "mapping_schema_version": question_mapping.get("mapping_schema_version"),
        "question_count": len(answers),
        "technical_question_count": len(technical_answers),
        "coverage_summary": {
            "evidence_class_counts": dict(sorted(evidence_counts.items())),
            "proposed_status_counts": dict(sorted(status_counts.items())),
            "section_counts": dict(sorted(section_counts.items())),
            "technical_evidence_class_counts": dict(sorted(technical_counts.items())),
            "cloud_supported_count": sum(
                evidence_counts.get(item, 0)
                for item in ("direct_cloud", "inferred_cloud")
            ),
            "technical_cloud_supported_count": sum(
                technical_counts.get(item, 0)
                for item in ("direct_cloud", "inferred_cloud")
            ),
            "requires_non_cloud_evidence_count": sum(
                evidence_counts.get(item, 0)
                for item in ("endpoint_required", "policy_required", "manual_required")
            ),
        },
        "answers": answers,
        "guardrails": [
            "Question text is paraphrased; IASME wording is not reproduced.",
            "Every entry remains human-reviewable before any certification submission.",
            "Endpoint, policy, and manual evidence requirements are surfaced instead of hidden.",
            "Direct and inferred cloud statuses are derived from existing CRIS-SME findings only.",
        ],
    }


def write_ce_self_assessment_pack(
    pack: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """Write a CE self-assessment pack JSON artifact."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pack, indent=2), encoding="utf-8")
    return path


def _build_answer_entry(
    question: dict[str, Any],
    risks_by_control: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    control_ids = [
        str(control_id)
        for control_id in question.get("supporting_control_ids", [])
        if str(control_id).strip()
    ]
    linked_risks = [
        risk
        for control_id in control_ids
        for risk in risks_by_control.get(control_id, [])
    ]
    evidence_class = str(question.get("evidence_class", "manual_required"))
    proposed_status = _proposed_status(evidence_class, control_ids, linked_risks)

    return {
        "question_id": str(question.get("question_id", "unknown")),
        "section": str(question.get("section", "unknown")),
        "research_scope": str(question.get("research_scope", "unknown")),
        "short_paraphrase": str(question.get("short_paraphrase", "")),
        "evidence_class": evidence_class,
        "proposed_status": proposed_status,
        "supporting_control_ids": control_ids,
        "linked_findings": [_compact_risk(risk) for risk in linked_risks],
        "evidence": _evidence_snippets(linked_risks),
        "current_cris_sme_signals": list(question.get("current_cris_sme_signals", [])),
        "planned_evidence_paths": list(question.get("planned_evidence_paths", [])),
        "human_review_required": bool(question.get("human_review_required", True)),
        "caveat": _caveat(evidence_class, proposed_status),
    }


def _proposed_status(
    evidence_class: str,
    control_ids: list[str],
    linked_risks: list[dict[str, Any]],
) -> str:
    if evidence_class == "endpoint_required":
        return "endpoint_required"
    if evidence_class == "policy_required":
        return "policy_required"
    if evidence_class == "manual_required":
        return "manual_required"
    if evidence_class == "not_observable":
        return "insufficient_evidence"
    if evidence_class in {"direct_cloud", "inferred_cloud"}:
        if linked_risks:
            return "supported_risk_found"
        if control_ids:
            return "supported_no_issue"
        return "insufficient_evidence"
    return "manual_required"


def _risks_by_control(report: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    risks = report.get("prioritized_risks", [])
    if not isinstance(risks, list):
        return grouped
    for risk in risks:
        if not isinstance(risk, dict):
            continue
        control_id = str(risk.get("control_id", "")).strip()
        if control_id:
            grouped[control_id].append(risk)
    return grouped


def _compact_risk(risk: dict[str, Any]) -> dict[str, Any]:
    return {
        "finding_id": risk.get("finding_id"),
        "control_id": risk.get("control_id"),
        "title": risk.get("title"),
        "priority": risk.get("priority"),
        "score": risk.get("score"),
        "evidence_quality": risk.get("evidence_quality", {}),
    }


def _evidence_snippets(linked_risks: list[dict[str, Any]]) -> list[str]:
    snippets: list[str] = []
    for risk in linked_risks:
        evidence = risk.get("evidence", [])
        if not isinstance(evidence, list):
            continue
        for item in evidence:
            text = str(item).strip()
            if text and text not in snippets:
                snippets.append(text)
            if len(snippets) >= 5:
                return snippets
    return snippets


def _caveat(evidence_class: str, proposed_status: str) -> str:
    if proposed_status == "supported_risk_found":
        return (
            "CRIS-SME found related cloud evidence that may affect this answer. "
            "A responsible person must verify the final Cyber Essentials response."
        )
    if proposed_status == "supported_no_issue":
        return (
            "No related CRIS-SME risk finding is currently present for the mapped controls. "
            "This is not a certification assertion and still requires human review."
        )
    if evidence_class == "endpoint_required":
        return (
            "This entry requires endpoint, MDM, EDR, patch, local firewall, or device "
            "inventory evidence outside the current cloud-control-plane scope."
        )
    if evidence_class == "policy_required":
        return (
            "This entry requires policy, process, approval, contractual, or business-need "
            "evidence that cannot be proven from cloud telemetry alone."
        )
    if evidence_class == "manual_required":
        return (
            "This entry requires human scoping, administrative context, or final applicant "
            "attestation."
        )
    return "Current CRIS-SME evidence is insufficient for pre-populating this entry."

