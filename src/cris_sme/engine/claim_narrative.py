# Deterministic narrative generation constrained to verified/caveated claim IDs.
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cris_sme.models.platform import (
    ClaimBoundNarrative,
    ClaimBoundNarrativeSection,
)


def build_claim_bound_narrative(report: dict[str, Any]) -> ClaimBoundNarrative:
    """Build a deterministic narrative that cites claim IDs and never invents claims."""
    claims = _claims(report)
    sections = [
        _summary_section(claims),
        _assurance_section(claims),
        _risk_section(claims),
        _readiness_section(claims),
        _insurance_section(claims),
    ]
    sections = [section for section in sections if section is not None]
    cited_claim_ids = sorted({claim_id for section in sections for claim_id in section.cited_claim_ids})
    return ClaimBoundNarrative(
        generated_at=_string_or_none(report.get("generated_at")),
        section_count=len(sections),
        cited_claim_count=len(cited_claim_ids),
        sections=sections,
        guardrails=[
            "Narrative is generated only from Claim Verification Pack claims.",
            "Verified claims may be stated plainly.",
            "Caveated claims must preserve caveat language.",
            "Unverified claims must be described as not verified.",
            "Narrative does not change deterministic CRIS-SME scores.",
        ],
        deterministic_score_impact=(
            "No impact. Claim-bound narrative explains verified/caveated claims and "
            "never changes deterministic CRIS-SME risk scores."
        ),
    )


def write_claim_bound_narrative(
    narrative: ClaimBoundNarrative,
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write claim-bound narrative JSON and Markdown artifacts."""
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    json_path = target_dir / "cris_sme_claim_bound_narrative.json"
    markdown_path = target_dir / "cris_sme_claim_bound_narrative.md"
    json_path.write_text(json.dumps(narrative.model_dump(mode="json"), indent=2), encoding="utf-8")
    markdown_path.write_text(build_claim_bound_narrative_markdown(narrative), encoding="utf-8")
    return {
        "claim_bound_narrative_json": json_path,
        "claim_bound_narrative_markdown": markdown_path,
    }


def build_claim_bound_narrative_markdown(narrative: ClaimBoundNarrative) -> str:
    """Render claim-bound narrative as Markdown with claim citations."""
    lines = [
        "# CRIS-SME Claim-Bound Narrative",
        "",
        f"- Generated at: `{narrative.generated_at or 'unknown'}`",
        f"- Narrative model: `{narrative.narrative_model}`",
        f"- Cited claims: `{narrative.cited_claim_count}`",
        "",
    ]
    for section in narrative.sections:
        lines.extend(
            [
                f"## {section.heading}",
                "",
                section.text,
                "",
                f"Supported claims: {', '.join(section.cited_claim_ids) or 'none'}",
                "",
            ]
        )
        if section.caveats:
            lines.extend(["Caveats:", ""])
            lines.extend(f"- {caveat}" for caveat in section.caveats)
            lines.append("")
    lines.extend(
        [
            "## Guardrails",
            "",
            *[f"- {guardrail}" for guardrail in narrative.guardrails],
            "",
            narrative.deterministic_score_impact,
            "",
        ]
    )
    return "\n".join(lines)


def _summary_section(claims: list[dict[str, Any]]) -> ClaimBoundNarrativeSection | None:
    overall = _first(claims, "overall_risk")
    trust = _first(claims, "trust_badge")
    selected = [claim for claim in (overall, trust) if claim]
    if not selected:
        return None
    text = " ".join(_claim_sentence(claim) for claim in selected)
    return _section("summary", "Executive Summary", text, selected)


def _assurance_section(claims: list[dict[str, Any]]) -> ClaimBoundNarrativeSection | None:
    selected = [claim for claim in (_first(claims, "replay"), _first(claims, "integrity")) if claim]
    if not selected:
        return None
    text = " ".join(_claim_sentence(claim) for claim in selected)
    return _section("assurance", "Replay And Integrity", text, selected)


def _risk_section(claims: list[dict[str, Any]]) -> ClaimBoundNarrativeSection | None:
    selected = [claim for claim in claims if claim.get("claim_type") == "top_risk"][:5]
    if not selected:
        return None
    text = " ".join(_claim_sentence(claim) for claim in selected)
    return _section("top_risks", "Top Risk Claims", text, selected)


def _readiness_section(claims: list[dict[str, Any]]) -> ClaimBoundNarrativeSection | None:
    selected = [
        claim
        for claim in claims
        if claim.get("claim_type") in {"cyber_essentials_readiness", "cyber_essentials_pillar"}
    ][:6]
    if not selected:
        return None
    text = " ".join(_claim_sentence(claim) for claim in selected)
    return _section("readiness", "Cyber Essentials Readiness", text, selected)


def _insurance_section(claims: list[dict[str, Any]]) -> ClaimBoundNarrativeSection | None:
    selected = [claim for claim in claims if claim.get("claim_type") == "insurance_question"][:6]
    if not selected:
        return None
    text = " ".join(_claim_sentence(claim) for claim in selected)
    return _section("insurance", "Insurance Evidence Claims", text, selected)


def _section(
    section_id: str,
    heading: str,
    text: str,
    selected_claims: list[dict[str, Any]],
) -> ClaimBoundNarrativeSection:
    return ClaimBoundNarrativeSection(
        section_id=section_id,
        heading=heading,
        text=text,
        cited_claim_ids=[str(claim.get("claim_id")) for claim in selected_claims],
        caveats=_caveats(selected_claims),
    )


def _claim_sentence(claim: dict[str, Any]) -> str:
    statement = str(claim.get("statement", "")).strip()
    status = str(claim.get("verification_status", "unknown"))
    claim_id = str(claim.get("claim_id", "claim"))
    if status == "verified":
        return f"{statement} [{claim_id}]"
    if status == "caveated":
        caveats = "; ".join(str(item) for item in claim.get("caveats", []) if str(item).strip())
        suffix = f" Caveat: {caveats}" if caveats else " Caveat recorded."
        return f"{statement} This claim is caveated.{suffix} [{claim_id}]"
    return f"{statement} This claim is not verified. [{claim_id}]"


def _claims(report: dict[str, Any]) -> list[dict[str, Any]]:
    pack = report.get("claim_verification_pack", {})
    if not isinstance(pack, dict):
        return []
    claims = pack.get("claims", [])
    return [claim for claim in claims if isinstance(claim, dict)] if isinstance(claims, list) else []


def _first(claims: list[dict[str, Any]], claim_type: str) -> dict[str, Any] | None:
    for claim in claims:
        if claim.get("claim_type") == claim_type:
            return claim
    return None


def _caveats(claims: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    caveats: list[str] = []
    for claim in claims:
        for caveat in claim.get("caveats", []):
            text = str(caveat).strip()
            if text and text not in seen:
                seen.add(text)
                caveats.append(text)
    return caveats


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
