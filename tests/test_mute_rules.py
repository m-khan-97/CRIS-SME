# Tests for operational mute rules and exception-aware risk score adjustment.
import json

from cris_sme.engine.lifecycle import (
    compute_adjusted_risk_scores,
    enrich_report_finding_lifecycle,
)
from cris_sme.models.platform import ExceptionRecord, FindingStatus, MuteRule


def _risk(**overrides) -> dict:
    base = {
        "finding_id": "finding-iam-001-org-a",
        "control_id": "IAM-001",
        "provider": "azure",
        "organization": "org-a",
        "resource_scope": "/subscriptions/sub-a/resourceGroups/rg-a",
        "category": "IAM",
        "score": 80.0,
    }
    base.update(overrides)
    return base


def _mute_rule(**overrides) -> MuteRule:
    base = dict(
        rule_id="mute-iam-001",
        name="Mute known IAM-001 finding in org-a",
        enabled=True,
        control_id="IAM-001",
        provider="azure",
        scope_pattern="*",
        reason="Compensating control documented separately for org-a.",
        created_by="security-lead",
        created_at="2026-06-01T00:00:00Z",
    )
    base.update(overrides)
    return MuteRule(**base)


def test_enabled_mute_rule_suppresses_matching_finding() -> None:
    report = {
        "generated_at": "2026-06-15T00:00:00Z",
        "prioritized_risks": [_risk()],
    }

    summary = enrich_report_finding_lifecycle(
        report,
        [],
        exception_registry=[],
        mute_rule_registry=[_mute_rule()],
    )

    lifecycle = report["prioritized_risks"][0]["lifecycle"]
    assert lifecycle["status"] == FindingStatus.SUPPRESSED.value
    assert lifecycle["mute_rule"]["rule_id"] == "mute-iam-001"
    assert summary["mute_rule_applied_count"] == 1


def test_disabled_mute_rule_does_not_suppress() -> None:
    report = {
        "generated_at": "2026-06-15T00:00:00Z",
        "prioritized_risks": [_risk()],
    }

    summary = enrich_report_finding_lifecycle(
        report,
        [],
        exception_registry=[],
        mute_rule_registry=[_mute_rule(enabled=False)],
    )

    lifecycle = report["prioritized_risks"][0]["lifecycle"]
    assert lifecycle["status"] == FindingStatus.OPEN.value
    assert summary["mute_rule_applied_count"] == 0


def test_expired_mute_rule_does_not_suppress() -> None:
    report = {
        "generated_at": "2026-06-15T00:00:00Z",
        "prioritized_risks": [_risk()],
    }

    summary = enrich_report_finding_lifecycle(
        report,
        [],
        exception_registry=[],
        mute_rule_registry=[_mute_rule(expires_at="2026-01-01T00:00:00Z")],
    )

    lifecycle = report["prioritized_risks"][0]["lifecycle"]
    assert lifecycle["status"] == FindingStatus.OPEN.value
    assert summary["mute_rule_applied_count"] == 0


def test_finding_id_pattern_must_match() -> None:
    report = {
        "generated_at": "2026-06-15T00:00:00Z",
        "prioritized_risks": [_risk(finding_id="finding-iam-001-org-b")],
    }

    summary = enrich_report_finding_lifecycle(
        report,
        [],
        exception_registry=[],
        mute_rule_registry=[_mute_rule(finding_id_pattern="*org-a")],
    )

    lifecycle = report["prioritized_risks"][0]["lifecycle"]
    assert lifecycle["status"] == FindingStatus.OPEN.value
    assert summary["mute_rule_applied_count"] == 0


def test_compute_adjusted_risk_scores_excludes_suppressed_findings() -> None:
    report = {
        "generated_at": "2026-06-15T00:00:00Z",
        "prioritized_risks": [
            _risk(score=80.0),
            _risk(
                finding_id="finding-net-001-org-a",
                control_id="NET-001",
                category="Network",
                score=40.0,
            ),
        ],
    }

    enrich_report_finding_lifecycle(
        report,
        [],
        exception_registry=[],
        mute_rule_registry=[_mute_rule()],
    )

    adjustment = compute_adjusted_risk_scores(report)

    assert adjustment["excluded_finding_count"] == 1
    assert adjustment["category_scores"]["IAM"] == 0.0
    assert adjustment["category_scores"]["Network"] == 40.0
    assert adjustment["overall_risk_score"] == round(40.0 * 0.20, 2)


def test_expired_exception_keeps_full_score_weight() -> None:
    report = {
        "generated_at": "2026-06-15T00:00:00Z",
        "prioritized_risks": [_risk()],
    }
    expired_exception = ExceptionRecord(
        exception_id="exc-iam-001",
        control_id="IAM-001",
        scope="any",
        provider="azure",
        reason="Temporary acceptance pending remediation window.",
        approved_by="security-lead",
        status=FindingStatus.ACCEPTED_RISK,
        expires_at="2026-01-01T00:00:00Z",
        created_at="2025-12-01T00:00:00Z",
    )

    enrich_report_finding_lifecycle(
        report,
        [],
        exception_registry=[expired_exception],
        mute_rule_registry=[],
    )

    lifecycle = report["prioritized_risks"][0]["lifecycle"]
    assert lifecycle["status"] == FindingStatus.EXPIRED_EXCEPTION.value

    adjustment = compute_adjusted_risk_scores(report)
    assert adjustment["excluded_finding_count"] == 0
    assert adjustment["category_scores"]["IAM"] == 80.0


def test_active_exception_excludes_finding_from_adjusted_score() -> None:
    report = {
        "generated_at": "2026-06-15T00:00:00Z",
        "prioritized_risks": [_risk()],
    }
    active_exception = ExceptionRecord(
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

    enrich_report_finding_lifecycle(
        report,
        [],
        exception_registry=[active_exception],
        mute_rule_registry=[],
    )

    lifecycle = report["prioritized_risks"][0]["lifecycle"]
    assert lifecycle["status"] == FindingStatus.ACCEPTED_RISK.value

    adjustment = compute_adjusted_risk_scores(report)
    assert adjustment["excluded_finding_count"] == 1
    assert adjustment["category_scores"]["IAM"] == 0.0


def test_mute_rule_cli_round_trip(tmp_path) -> None:
    from cris_sme.cli import mute_rules

    registry_path = tmp_path / "mute_rules.json"
    registry_path.write_text("[]", encoding="utf-8")

    assert (
        mute_rules.main(
            [
                "--path",
                str(registry_path),
                "add",
                "mute-iam-001",
                "Mute IAM-001 in org-a",
                "Compensating control documented.",
                "security-lead",
                "--control-id",
                "IAM-001",
            ]
        )
        == 0
    )

    rules = json.loads(registry_path.read_text(encoding="utf-8"))
    assert len(rules) == 1
    assert rules[0]["rule_id"] == "mute-iam-001"
    assert rules[0]["enabled"] is True

    assert (
        mute_rules.main(["--path", str(registry_path), "disable", "mute-iam-001"]) == 0
    )
    rules = json.loads(registry_path.read_text(encoding="utf-8"))
    assert rules[0]["enabled"] is False

    assert (
        mute_rules.main(["--path", str(registry_path), "enable", "mute-iam-001"]) == 0
    )
    rules = json.loads(registry_path.read_text(encoding="utf-8"))
    assert rules[0]["enabled"] is True

    assert (
        mute_rules.main(["--path", str(registry_path), "remove", "mute-iam-001"]) == 0
    )
    rules = json.loads(registry_path.read_text(encoding="utf-8"))
    assert rules == []
