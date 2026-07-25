# Tests for executable provider evidence contract conformance gates.
from cris_sme.engine.provider_conformance import (
    build_provider_contract_conformance_report,
    summarize_provider_contract_conformance,
)


def test_provider_contract_conformance_matches_declared_support() -> None:
    report = build_provider_contract_conformance_report()

    assert report.passed is True
    assert report.provider_count == 3
    assert report.control_count == 36
    assert report.active_contract_count == 26
    assert report.planned_contract_count == 36
    assert report.failed_contract_count == 0
    assert report.passed_contract_count == 108
    assert all(
        "contract_metadata_complete" in check.required_signals
        for check in report.checks
    )
    assert all(
        "contract_metadata_complete" in check.satisfied_signals
        for check in report.checks
    )


def test_provider_contract_conformance_distinguishes_active_and_planned() -> None:
    report = build_provider_contract_conformance_report()
    signals = {signal.provider: signal for signal in report.provider_signals}

    assert signals["azure"].adapter_registered is True
    assert signals["azure"].live_collector_present is True
    assert signals["azure"].collector_tests_present is True
    assert signals["azure"].docs_present is True
    assert signals["azure"].status == "active_ready"

    assert signals["aws"].adapter_registered is True
    assert signals["aws"].live_collector_present is False
    assert signals["aws"].collector_tests_present is True
    assert signals["aws"].docs_present is True
    assert signals["aws"].status == "partial"

    assert signals["gcp"].adapter_registered is False
    assert signals["gcp"].live_collector_present is False
    assert signals["gcp"].docs_present is True
    assert signals["gcp"].status == "planned_ready"


def test_provider_contract_conformance_validates_richer_metadata() -> None:
    report = build_provider_contract_conformance_report()
    azure_check = next(
        check
        for check in report.checks
        if check.provider == "azure" and check.control_id == "NET-001"
    )
    aws_check = next(
        check
        for check in report.checks
        if check.provider == "aws" and check.control_id == "NET-001"
    )

    assert azure_check.passed is True
    assert "adapter_registered" in azure_check.satisfied_signals
    assert "contract_metadata_complete" in azure_check.satisfied_signals
    assert aws_check.passed is True
    assert "docs_present" in aws_check.satisfied_signals
    assert "contract_metadata_complete" in aws_check.satisfied_signals


def test_provider_contract_conformance_dashboard_summary() -> None:
    report = build_provider_contract_conformance_report()
    summary = summarize_provider_contract_conformance(report)

    assert summary["passed"] is True
    assert summary["active_contract_count"] == 26
    assert summary["planned_contract_count"] == 36
    assert summary["failed_contract_count"] == 0
