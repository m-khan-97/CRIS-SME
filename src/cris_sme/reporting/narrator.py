# Optional LLM narrator for translating deterministic CRIS-SME reports into plain language.
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import json
from typing import Any, Callable
from urllib import error, request

from pydantic import BaseModel, Field


ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"

Transport = Callable[[request.Request, int], dict[str, Any]]


@dataclass(slots=True)
class NarratorSettings:
    """Runtime configuration for the optional plain-language narrator."""

    enabled: bool = False
    provider: str = "anthropic"
    api_key: str | None = None
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 1400
    temperature: float = 0.2
    timeout_seconds: int = 45


class PlainLanguageNarrative(BaseModel):
    """Narrator outputs designed for different SME stakeholders."""

    provider: str = Field(..., min_length=2)
    model: str = Field(..., min_length=3)
    generated_at: str = Field(..., min_length=10)
    executive_narrative: str = Field(..., min_length=20)
    owner_action_plan: str = Field(..., min_length=20)
    board_brief: str = Field(..., min_length=20)
    disclaimer: str = Field(..., min_length=10)


def maybe_generate_plain_language_narrative(
    report: dict[str, Any],
    settings: NarratorSettings,
    transport: Transport | None = None,
) -> PlainLanguageNarrative | None:
    """Generate optional plain-language narration without affecting scoring/report math."""
    if not settings.enabled or not settings.api_key:
        return None

    if settings.provider != "anthropic":
        raise ValueError(
            f"Unsupported narrator provider '{settings.provider}'. "
            "Only 'anthropic' is currently implemented."
        )

    payload = _build_anthropic_payload(report, settings)
    response = _invoke_anthropic_messages_api(
        payload=payload,
        settings=settings,
        transport=transport,
    )
    text = _extract_text_from_response(response)
    parsed = _parse_json_object(text)
    generated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    disclaimer = (
        "This narrative is LLM-generated from deterministic CRIS-SME results. "
        "Scores and evidence remain authoritative in the underlying report."
    )

    if parsed is None:
        return PlainLanguageNarrative(
            provider=settings.provider,
            model=settings.model,
            generated_at=generated_at,
            executive_narrative=text.strip() or "No narrative text was returned.",
            owner_action_plan=(
                "Review the deterministic remediation guidance in the CRIS-SME report "
                "because the narrator response was not returned in structured form."
            ),
            board_brief=(
                "CRIS-SME produced a plain-language response, but it did not match the "
                "expected structure for stakeholder-ready output."
            ),
            disclaimer=disclaimer,
        )

    return PlainLanguageNarrative(
        provider=settings.provider,
        model=settings.model,
        generated_at=generated_at,
        executive_narrative=str(
            parsed.get("executive_narrative", "No executive narrative was returned.")
        ).strip(),
        owner_action_plan=str(
            parsed.get("owner_action_plan", "No owner action plan was returned.")
        ).strip(),
        board_brief=str(parsed.get("board_brief", "No board brief was returned.")).strip(),
        disclaimer=disclaimer,
    )


def write_plain_language_reports(
    narrative: PlainLanguageNarrative,
    output_dir: str | Path,
) -> dict[str, Path]:
    """Persist narrator outputs as markdown artifacts for demos and stakeholder sharing."""
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    plain_language_path = target_dir / "cris_sme_plain_language.md"
    board_brief_path = target_dir / "cris_sme_board_brief.md"

    plain_language_path.write_text(
        "\n".join(
            [
                "# CRIS-SME Plain-Language Narrative",
                "",
                f"- Provider: `{narrative.provider}`",
                f"- Model: `{narrative.model}`",
                f"- Generated at: `{narrative.generated_at}`",
                "",
                "## Executive Narrative",
                "",
                narrative.executive_narrative,
                "",
                "## Owner Action Plan",
                "",
                narrative.owner_action_plan,
                "",
                "## Disclaimer",
                "",
                narrative.disclaimer,
                "",
            ]
        ),
        encoding="utf-8",
    )

    board_brief_path.write_text(
        "\n".join(
            [
                "# CRIS-SME Board Brief",
                "",
                f"- Provider: `{narrative.provider}`",
                f"- Model: `{narrative.model}`",
                f"- Generated at: `{narrative.generated_at}`",
                "",
                narrative.board_brief,
                "",
                "## Disclaimer",
                "",
                narrative.disclaimer,
                "",
            ]
        ),
        encoding="utf-8",
    )

    return {
        "plain_language_markdown": plain_language_path,
        "board_brief_markdown": board_brief_path,
    }


def _build_anthropic_payload(
    report: dict[str, Any],
    settings: NarratorSettings,
) -> dict[str, Any]:
    """Build a compact Anthropic Messages API request payload."""
    compact_report = _build_compact_report_context(report)
    return {
        "model": settings.model,
        "max_tokens": settings.max_tokens,
        "temperature": settings.temperature,
        "system": (
            "You are writing plain-language cyber risk communication for UK SMEs. "
            "Preserve the exact scores, counts, and findings from the provided "
            "deterministic report. Do not invent new evidence, costs, controls, or "
            "compliance claims. Respond as strict JSON with keys "
            "executive_narrative, owner_action_plan, and board_brief. "
            "Make the language accessible to non-specialists but keep it grounded."
        ),
        "messages": [
            {
                "role": "user",
                "content": (
                    "Translate this CRIS-SME assessment into plain-language outputs for "
                    "different audiences.\n\n"
                    f"{json.dumps(compact_report, indent=2)}"
                ),
            }
        ],
    }


def _build_compact_report_context(report: dict[str, Any]) -> dict[str, Any]:
    """Reduce the full report into a compact prompt context for the narrator."""
    organizations = report.get("organizations", [])
    prioritized_risks = report.get("prioritized_risks", [])
    budget_profiles = (
        report.get("budget_aware_remediation", {}).get("budget_profiles", [])
        if isinstance(report.get("budget_aware_remediation", {}), dict)
        else []
    )
    uk_profile = (
        report.get("compliance", {}).get("uk_sme_profile", {})
        if isinstance(report.get("compliance", {}), dict)
        else {}
    )

    compact_risks: list[dict[str, Any]] = []
    if isinstance(prioritized_risks, list):
        for risk in prioritized_risks[:5]:
            if not isinstance(risk, dict):
                continue
            compact_risks.append(
                {
                    "control_id": risk.get("control_id"),
                    "title": risk.get("title"),
                    "category": risk.get("category"),
                    "priority": risk.get("priority"),
                    "score": risk.get("score"),
                    "organization": risk.get("organization"),
                    "remediation_cost_tier": risk.get("remediation_cost_tier"),
                    "remediation_value_score": risk.get("remediation_value_score"),
                    "remediation_summary": risk.get("remediation_summary"),
                    "evidence": risk.get("evidence", [])[:2],
                }
            )

    compact_budget_profiles: list[dict[str, Any]] = []
    if isinstance(budget_profiles, list):
        for profile in budget_profiles:
            if not isinstance(profile, dict):
                continue
            actions = profile.get("recommended_actions", [])
            if not isinstance(actions, list):
                actions = []
            compact_budget_profiles.append(
                {
                    "profile_id": profile.get("profile_id"),
                    "label": profile.get("label"),
                    "max_monthly_cost_gbp": profile.get("max_monthly_cost_gbp"),
                    "total_recommended": profile.get("total_recommended"),
                    "cumulative_risk_score": profile.get("cumulative_risk_score"),
                    "top_actions": [
                        {
                            "control_id": action.get("control_id"),
                            "title": action.get("title"),
                            "score": action.get("score"),
                            "remediation_cost_tier": action.get("remediation_cost_tier"),
                            "remediation_value_score": action.get(
                                "remediation_value_score"
                            ),
                        }
                        for action in actions[:3]
                        if isinstance(action, dict)
                    ],
                }
            )

    return {
        "overall_risk_score": report.get("overall_risk_score"),
        "summary": report.get("summary"),
        "executive_summary": report.get("executive_summary"),
        "evaluation_context": report.get("evaluation_context"),
        "category_scores": report.get("category_scores"),
        "organizations": organizations,
        "top_risks": compact_risks,
        "uk_sme_profile": uk_profile,
        "budget_aware_remediation": compact_budget_profiles,
    }


def _invoke_anthropic_messages_api(
    *,
    payload: dict[str, Any],
    settings: NarratorSettings,
    transport: Transport | None = None,
) -> dict[str, Any]:
    """Send a request to the Anthropic Messages API."""
    if transport is None:
        transport = _default_transport

    req = request.Request(
        url=ANTHROPIC_MESSAGES_URL,
        method="POST",
        headers={
            "x-api-key": settings.api_key or "",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        data=json.dumps(payload).encode("utf-8"),
    )
    return transport(req, settings.timeout_seconds)


def _default_transport(req: request.Request, timeout_seconds: int) -> dict[str, Any]:
    """Default HTTPS transport for narrator requests."""
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Anthropic narrator request failed with HTTP {exc.code}: {body}"
        ) from exc
    except error.URLError as exc:
        raise RuntimeError(f"Anthropic narrator request failed: {exc.reason}") from exc


def _extract_text_from_response(response: dict[str, Any]) -> str:
    """Extract text content from an Anthropic Messages API response."""
    content = response.get("content", [])
    if not isinstance(content, list):
        return ""

    text_fragments = [
        str(item.get("text", ""))
        for item in content
        if isinstance(item, dict) and item.get("type") == "text"
    ]
    return "\n".join(fragment for fragment in text_fragments if fragment.strip()).strip()


def _parse_json_object(text: str) -> dict[str, Any] | None:
    """Parse a JSON object from narrator text, including simple fenced/fallback cases."""
    stripped = text.strip()
    if not stripped:
        return None

    candidate = stripped
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
        if candidate.startswith("json"):
            candidate = candidate[4:].strip()

    for raw in (candidate, _extract_braced_json(candidate)):
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    return None


def _extract_braced_json(text: str) -> str | None:
    """Return the substring between the first and last JSON braces if present."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]
