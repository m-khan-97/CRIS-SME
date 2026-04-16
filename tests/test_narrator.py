# Unit tests for the optional plain-language narrator in CRIS-SME.
from urllib import request

from cris_sme.reporting.narrator import (
    NarratorSettings,
    maybe_generate_plain_language_narrative,
    write_plain_language_reports,
)


def make_report() -> dict[str, object]:
    """Create a compact report payload for narrator testing."""
    return {
        "overall_risk_score": 33.12,
        "summary": "Overall risk score: 33.12/100 across 16 non-compliant findings.",
        "executive_summary": "Deterministic summary placeholder.",
        "evaluation_context": {
            "evaluated_profiles": 1,
            "generated_findings": 16,
            "non_compliant_findings": 15,
        },
        "category_scores": {
            "IAM": 14.64,
            "Network": 47.41,
        },
        "organizations": [
            {
                "organization_name": "Azure SME Tenant",
                "collection_details": {
                    "collector_stage": "azure_live_enriched",
                    "subscription_display_name": "Azure for Students",
                },
            }
        ],
        "prioritized_risks": [
            {
                "control_id": "NET-001",
                "title": "Administrative services are exposed to the public internet",
                "category": "Network",
                "priority": "High",
                "score": 50.33,
                "organization": "Azure SME Tenant",
                "remediation_cost_tier": "medium",
                "remediation_value_score": 27.21,
                "remediation_summary": "Restrict SSH and RDP exposure.",
                "evidence": ["3 SSH-exposed assets"],
            }
        ],
        "budget_aware_remediation": {
            "budget_profiles": [
                {
                    "profile_id": "free_this_week",
                    "label": "Free fixes this week",
                    "max_monthly_cost_gbp": 0,
                    "total_recommended": 5,
                    "cumulative_risk_score": 174.9,
                    "recommended_actions": [],
                }
            ]
        },
        "compliance": {
            "uk_sme_profile": {
                "frameworks_covered": ["Cyber Essentials", "UK GDPR"],
                "mapped_control_count": 7,
                "mapped_finding_count": 6,
            }
        },
    }


def fake_transport(_req: request.Request, _timeout_seconds: int) -> dict[str, object]:
    """Return a valid Anthropic-style response payload for narrator tests."""
    return {
        "content": [
            {
                "type": "text",
                "text": (
                    '{'
                    '"executive_narrative":"Your biggest current risk is public administrative exposure.",'
                    '"owner_action_plan":"Fix the free identity and firewall issues first, then tackle medium-cost workload protections.",'
                    '"board_brief":"CRIS-SME identified manageable but material cloud governance risks that should be reduced in staged budget bands."'
                    '}'
                ),
            }
        ]
    }


def test_maybe_generate_plain_language_narrative_returns_structured_output() -> None:
    settings = NarratorSettings(
        enabled=True,
        api_key="test-key",
        model="claude-sonnet-4-20250514",
    )

    narrative = maybe_generate_plain_language_narrative(
        make_report(),
        settings,
        transport=fake_transport,
    )

    assert narrative is not None
    assert narrative.provider == "anthropic"
    assert "public administrative exposure" in narrative.executive_narrative
    assert "budget bands" in narrative.board_brief


def test_maybe_generate_plain_language_narrative_skips_when_disabled() -> None:
    settings = NarratorSettings(enabled=False, api_key="test-key")

    narrative = maybe_generate_plain_language_narrative(
        make_report(),
        settings,
        transport=fake_transport,
    )

    assert narrative is None


def test_write_plain_language_reports_persists_markdown_outputs(tmp_path) -> None:
    settings = NarratorSettings(
        enabled=True,
        api_key="test-key",
        model="claude-sonnet-4-20250514",
    )
    narrative = maybe_generate_plain_language_narrative(
        make_report(),
        settings,
        transport=fake_transport,
    )
    assert narrative is not None

    paths = write_plain_language_reports(narrative, tmp_path)

    plain_language = paths["plain_language_markdown"].read_text(encoding="utf-8")
    board_brief = paths["board_brief_markdown"].read_text(encoding="utf-8")

    assert "CRIS-SME Plain-Language Narrative" in plain_language
    assert "Owner Action Plan" in plain_language
    assert "CRIS-SME Board Brief" in board_brief
