# Tests for CRIS-SME MCP tool query functions.
import json

from cris_sme.mcp import tools
from cris_sme.models.platform import ExceptionRecord, FindingStatus, MuteRule


def _report() -> dict:
    return {
        "generated_at": "2026-06-15T00:00:00Z",
        "collector_mode": "mock",
        "report_schema_version": "2.0.0",
        "overall_risk_score": 39.84,
        "category_scores": {"IAM": 60.0, "Network": 40.0},
        "adjusted_risk_scores": {"overall_risk_score": 30.0, "excluded_finding_count": 1},
        "evidence_snapshot": {"snapshot_id": "evs_abc123"},
        "risk_bill_of_materials": {"canonical_report_sha256": "a" * 64},
        "finding_lifecycle_summary": {"status_counts": {"open": 1, "suppressed": 1}},
        "prioritized_risks": [
            {
                "finding_id": "fdg_aaa111",
                "control_id": "IAM-001",
                "title": "Privileged accounts without MFA",
                "severity": "Critical",
                "category": "IAM",
                "score": 82.84,
                "priority": "Immediate",
                "organization": "Org A",
                "resource_scope": "Tenant root",
                "asset_ids": ["identity:azure:org-a"],
                "evidence_ids": ["evd_fdg_aaa111_01"],
                "lifecycle": {"status": "open"},
            },
            {
                "finding_id": "fdg_bbb222",
                "control_id": "NET-001",
                "title": "RDP exposed to internet",
                "severity": "High",
                "category": "Network",
                "score": 60.0,
                "priority": "High",
                "organization": "Org A",
                "resource_scope": "Tenant root",
                "asset_ids": ["network:azure:org-a"],
                "evidence_ids": ["evd_fdg_bbb222_01"],
                "lifecycle": {"status": "suppressed"},
            },
        ],
        "resource_context": {
            "evidence_records": [
                {
                    "evidence_id": "evd_fdg_aaa111_01",
                    "provider": "azure",
                    "collector": "iam_controls",
                    "record_type": "control_evidence/IAM-001",
                    "observation_class": "observed",
                    "observed_at": "2026-06-15T00:00:00Z",
                    "payload": {
                        "finding_id": "fdg_aaa111",
                        "control_id": "IAM-001",
                        "resource_scope": "Tenant root",
                        "statement": "2 privileged accounts lack MFA",
                    },
                },
            ],
        },
        "claim_verification_pack": {
            "claims": [
                {
                    "claim_id": "clm_xyz789",
                    "claim_type": "overall_risk",
                    "audience": "executive",
                    "statement": "Overall CRIS-SME risk score is 39.84/100.",
                    "verification_status": "verified",
                    "confidence": 0.95,
                    "evidence_refs": ["evd_fdg_aaa111_01"],
                },
            ],
        },
        "action_plan_30_day": {
            "plan_name": "30-day plan",
            "phases": [
                {
                    "phase_id": "days_1_7",
                    "label": "Fix this week",
                    "time_window": "Days 1-7",
                    "actions": [
                        {
                            "control_id": "IAM-001",
                            "title": "Require MFA for privileged roles",
                            "organization": "Org A",
                            "category": "IAM",
                            "priority": "Immediate",
                            "score": 82.84,
                            "remediation_cost_tier": "free",
                            "remediation_summary": "Enforce MFA for admins.",
                            "action_rationale": "Critical and free to fix.",
                        }
                    ],
                }
            ],
        },
    }


def test_load_report_reads_json(tmp_path) -> None:
    report = _report()
    path = tmp_path / "cris_sme_report.json"
    path.write_text(json.dumps(report), encoding="utf-8")

    loaded = tools.load_report(path)
    assert loaded["generated_at"] == "2026-06-15T00:00:00Z"


def test_get_assessment_summary_cites_snapshot_and_score() -> None:
    summary = tools.get_assessment_summary(_report())

    assert summary["overall_risk_score"] == 39.84
    assert summary["evidence_snapshot_id"] == "evs_abc123"
    assert summary["risk_bill_of_materials_sha256"] == "a" * 64
    assert summary["finding_count"] == 2


def test_list_findings_filters_by_severity_and_lifecycle_status() -> None:
    report = _report()

    critical = tools.list_findings(report, severity="critical")
    assert [f["finding_id"] for f in critical] == ["fdg_aaa111"]

    suppressed = tools.list_findings(report, lifecycle_status="suppressed")
    assert [f["finding_id"] for f in suppressed] == ["fdg_bbb222"]

    by_org = tools.list_findings(report, organization="Org A", control_id="NET-001")
    assert [f["finding_id"] for f in by_org] == ["fdg_bbb222"]


def test_get_finding_returns_full_record_or_none() -> None:
    report = _report()

    finding = tools.get_finding(report, "fdg_aaa111")
    assert finding is not None
    assert finding["title"] == "Privileged accounts without MFA"

    assert tools.get_finding(report, "fdg_missing") is None


def test_list_evidence_filters_by_finding_and_control_id() -> None:
    report = _report()

    by_finding = tools.list_evidence(report, finding_id="fdg_aaa111")
    assert [e["evidence_id"] for e in by_finding] == ["evd_fdg_aaa111_01"]

    by_control = tools.list_evidence(report, control_id="IAM-001")
    assert [e["evidence_id"] for e in by_control] == ["evd_fdg_aaa111_01"]

    assert tools.list_evidence(report, control_id="NET-001") == []


def test_list_claims_filters_by_type_and_status() -> None:
    report = _report()

    claims = tools.list_claims(report, claim_type="overall_risk")
    assert [c["claim_id"] for c in claims] == ["clm_xyz789"]

    assert tools.list_claims(report, verification_status="caveated") == []


def test_list_action_plan_filters_by_phase() -> None:
    report = _report()

    actions = tools.list_action_plan(report, phase_id="days_1_7")
    assert [a["control_id"] for a in actions] == ["IAM-001"]

    assert tools.list_action_plan(report, phase_id="days_8_30") == []


def test_list_exceptions_and_mute_rules_use_registries() -> None:
    exception = ExceptionRecord(
        exception_id="exc-iam-001",
        control_id="IAM-001",
        scope="any",
        provider="azure",
        reason="Documented compensating control covers this finding.",
        approved_by="security-lead",
        status=FindingStatus.ACCEPTED_RISK,
        expires_at="2099-01-01T00:00:00Z",
        created_at="2026-01-01T00:00:00Z",
    )
    rule = MuteRule(
        rule_id="mute-iam-001",
        name="Mute IAM-001 in org-a",
        control_id="IAM-001",
        reason="Compensating control documented separately.",
        created_by="security-lead",
        created_at="2026-06-01T00:00:00Z",
    )

    exceptions = tools.list_exceptions(exception_registry=[exception])
    assert exceptions[0]["exception_id"] == "exc-iam-001"

    rules = tools.list_mute_rules(mute_rule_registry=[rule])
    assert rules[0]["rule_id"] == "mute-iam-001"
