# Cyber insurance evidence pack generation for insurer-facing CRIS-SME outputs.
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_cyber_insurance_evidence_pack(report: dict[str, Any]) -> dict[str, Any]:
    """Build an insurer-facing evidence summary from the current CRIS-SME report."""
    catalog = _load_insurance_question_catalog()
    prioritized_risks = report.get("prioritized_risks", [])
    if not isinstance(prioritized_risks, list):
        prioritized_risks = []

    risks_by_control = {
        str(item.get("control_id")): item
        for item in prioritized_risks
        if isinstance(item, dict) and item.get("control_id")
    }

    question_summaries = [
        _build_question_summary(entry, risks_by_control)
        for entry in catalog
    ]

    readiness = {
        "met": sum(1 for item in question_summaries if item["status"] == "met"),
        "partial": sum(1 for item in question_summaries if item["status"] == "partial"),
        "not_met": sum(1 for item in question_summaries if item["status"] == "not_met"),
        "unknown": sum(1 for item in question_summaries if item["status"] == "unknown"),
    }
    readiness_score = round(
        (
            readiness["met"] * 1.0
            + readiness["partial"] * 0.5
            + readiness["unknown"] * 0.25
        )
        / max(len(question_summaries), 1)
        * 100.0,
        2,
    )

    organizations = report.get("organizations", [])
    if not isinstance(organizations, list):
        organizations = []

    return {
        "pack_name": "CRIS-SME Cyber Insurance Evidence Pack",
        "jurisdiction": "United Kingdom",
        "generated_at": report.get("generated_at"),
        "collector_mode": report.get("collector_mode"),
        "overall_risk_score": report.get("overall_risk_score"),
        "organizations": [
            {
                "organization_id": org.get("organization_id"),
                "organization_name": org.get("organization_name"),
                "provider": org.get("provider"),
                "sector": org.get("sector"),
            }
            for org in organizations
            if isinstance(org, dict)
        ],
        "readiness_summary": {
            "question_count": len(question_summaries),
            "met_count": readiness["met"],
            "partial_count": readiness["partial"],
            "not_met_count": readiness["not_met"],
            "unknown_count": readiness["unknown"],
            "readiness_score": readiness_score,
        },
        "questions": question_summaries,
        "disclaimer": (
            "This evidence pack is an insurer-facing technical summary derived from the "
            "deterministic CRIS-SME assessment. It is not legal, regulatory, or insurance "
            "advice and should be reviewed alongside the organisation's formal insurance application."
        ),
    }


def write_cyber_insurance_evidence_pack(
    insurance_pack: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write insurer-facing evidence pack artifacts to disk."""
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    markdown_path = target_dir / "cris_sme_cyber_insurance_evidence.md"
    json_path = target_dir / "cris_sme_cyber_insurance_evidence.json"

    markdown_path.write_text(
        build_cyber_insurance_markdown(insurance_pack),
        encoding="utf-8",
    )
    json_path.write_text(json.dumps(insurance_pack, indent=2), encoding="utf-8")

    return {
        "cyber_insurance_markdown": markdown_path,
        "cyber_insurance_json": json_path,
    }


def build_cyber_insurance_markdown(insurance_pack: dict[str, Any]) -> str:
    """Render the insurer-facing evidence pack as concise Markdown."""
    readiness = insurance_pack.get("readiness_summary", {})
    if not isinstance(readiness, dict):
        readiness = {}

    organizations = insurance_pack.get("organizations", [])
    if not isinstance(organizations, list):
        organizations = []
    organization_summary = ", ".join(
        str(item.get("organization_name", "Unknown organisation"))
        for item in organizations
        if isinstance(item, dict)
    ) or "No organisation metadata recorded"

    lines = [
        "# CRIS-SME Cyber Insurance Evidence Pack",
        "",
        f"- Generated at: `{insurance_pack.get('generated_at', 'unknown')}`",
        f"- Jurisdiction: `{insurance_pack.get('jurisdiction', 'unknown')}`",
        f"- Collector mode: `{insurance_pack.get('collector_mode', 'unknown')}`",
        f"- Organizations: {organization_summary}",
        f"- Overall risk score: `{float(insurance_pack.get('overall_risk_score', 0.0)):.2f}`",
        f"- Readiness score: `{float(readiness.get('readiness_score', 0.0)):.2f}`",
        "",
        "## Readiness Summary",
        "",
        f"- Questions assessed: `{int(readiness.get('question_count', 0))}`",
        f"- Met: `{int(readiness.get('met_count', 0))}`",
        f"- Partial: `{int(readiness.get('partial_count', 0))}`",
        f"- Not met: `{int(readiness.get('not_met_count', 0))}`",
        f"- Unknown: `{int(readiness.get('unknown_count', 0))}`",
        "",
        "## Question-Level Evidence",
        "",
    ]

    questions = insurance_pack.get("questions", [])
    if not isinstance(questions, list):
        questions = []

    for question in questions:
        if not isinstance(question, dict):
            continue
        lines.extend(
            [
                f"### {question.get('question_id', 'INS-?')} - {question.get('theme', 'Unknown theme')}",
                "",
                f"- Question: {question.get('question', '')}",
                f"- Status: `{question.get('status', 'unknown')}`",
                f"- Evidence statement: {question.get('evidence_statement', '')}",
                f"- Insurer relevance: {question.get('insurer_relevance', '')}",
                f"- Recommended next step: {question.get('recommended_next_step', '')}",
                f"- Related controls: {', '.join(question.get('related_controls', []))}",
                "",
            ]
        )
        supporting_findings = question.get("supporting_findings", [])
        if isinstance(supporting_findings, list) and supporting_findings:
            lines.extend(
                [
                    "| Control | Priority | Score | Evidence |",
                    "| --- | --- | ---: | --- |",
                ]
            )
            for finding in supporting_findings:
                if not isinstance(finding, dict):
                    continue
                evidence_items = finding.get("evidence", [])
                if not isinstance(evidence_items, list):
                    evidence_items = []
                evidence_summary = "; ".join(str(item) for item in evidence_items[:2])
                lines.append(
                    "| "
                    f"{finding.get('control_id', '')} | "
                    f"{finding.get('priority', '')} | "
                    f"{float(finding.get('score', 0.0)):.2f} | "
                    f"{evidence_summary} |"
                )
            lines.append("")

    disclaimer = insurance_pack.get("disclaimer")
    if disclaimer:
        lines.extend(
            [
                "## Disclaimer",
                "",
                str(disclaimer),
                "",
            ]
        )

    return "\n".join(lines)


def _build_question_summary(
    entry: dict[str, Any],
    risks_by_control: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Derive a concise insurer-facing question summary from linked controls."""
    related_controls = [
        str(control_id)
        for control_id in entry.get("related_controls", [])
        if str(control_id).strip()
    ]
    failing_findings = [
        risks_by_control[control_id]
        for control_id in related_controls
        if control_id in risks_by_control
    ]

    status = _derive_question_status(related_controls, failing_findings)
    evidence_statement = _build_evidence_statement(
        status=status,
        question=entry,
        failing_findings=failing_findings,
    )
    recommended_next_step = _build_recommended_next_step(
        status=status,
        failing_findings=failing_findings,
    )

    return {
        "question_id": entry.get("question_id", "INS-?"),
        "theme": entry.get("theme", "Unknown theme"),
        "question": entry.get("question", ""),
        "status": status,
        "insurer_relevance": entry.get("insurer_relevance", ""),
        "primary_control_id": entry.get("primary_control_id"),
        "related_controls": related_controls,
        "supporting_findings": [
            {
                "control_id": item.get("control_id"),
                "title": item.get("title"),
                "priority": item.get("priority"),
                "score": item.get("score"),
                "evidence": item.get("evidence", []),
                "remediation_summary": item.get("remediation_summary"),
            }
            for item in failing_findings
        ],
        "evidence_statement": evidence_statement,
        "recommended_next_step": recommended_next_step,
    }


def _derive_question_status(
    related_controls: list[str],
    failing_findings: list[dict[str, Any]],
) -> str:
    """Translate linked CRIS-SME findings into a simple insurer-facing status."""
    if not related_controls:
        return "unknown"
    if not failing_findings:
        return "met"

    failing_ids = {
        str(item.get("control_id"))
        for item in failing_findings
        if item.get("control_id")
    }
    if "IAM-005" in failing_ids:
        return "partial"
    if len(failing_ids) >= len(related_controls):
        return "not_met"
    return "partial"


def _build_evidence_statement(
    *,
    status: str,
    question: dict[str, Any],
    failing_findings: list[dict[str, Any]],
) -> str:
    """Build a concise insurer-facing answer for a question summary."""
    theme = str(question.get("theme", "control area")).lower()

    if status == "met":
        return (
            f"No active CRIS-SME finding currently indicates a material gap in {theme} "
            "for the mapped controls in this report."
        )

    if not failing_findings:
        return (
            "CRIS-SME could not determine a complete answer for this insurance question "
            "from the currently observed evidence set."
        )

    top = failing_findings[0]
    top_control = str(top.get("control_id", "control"))
    top_priority = str(top.get("priority", "Monitor")).lower()
    top_score = float(top.get("score", 0.0))

    if status == "not_met":
        return (
            f"CRIS-SME identified material evidence that this control area is not fully met. "
            f"The strongest linked gap is {top_control} at {top_score:.2f} risk ({top_priority} priority)."
        )

    return (
        f"CRIS-SME identified partial evidence of control weakness or incomplete observability. "
        f"The strongest linked gap is {top_control} at {top_score:.2f} risk ({top_priority} priority)."
    )


def _build_recommended_next_step(
    *,
    status: str,
    failing_findings: list[dict[str, Any]],
) -> str:
    """Choose the most practical next step to strengthen insurer-facing evidence."""
    if status == "met":
        return (
            "Retain supporting configuration evidence and review the mapped controls at the next scheduled assessment."
        )
    if not failing_findings:
        return (
            "Broaden evidence collection for this question before relying on the result in an insurance submission."
        )
    top = failing_findings[0]
    remediation_summary = str(top.get("remediation_summary", "")).strip()
    if remediation_summary:
        return remediation_summary
    return "Review the linked control findings and implement the highest-priority remediation."


def _load_insurance_question_catalog() -> list[dict[str, Any]]:
    """Load the cyber insurance question catalog from the project data directory."""
    catalog_path = Path(__file__).resolve().parents[3] / "data" / "cyber_insurance_questions.json"
    raw_catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(raw_catalog, list):
        raise ValueError("Cyber insurance question catalog must be a list.")
    return [entry for entry in raw_catalog if isinstance(entry, dict)]
