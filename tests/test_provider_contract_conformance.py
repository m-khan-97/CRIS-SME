# Tests for executable provider evidence contract conformance gates.
from cris_sme.engine.provider_conformance import (
    build_provider_contract_conformance_report,
    summarize_provider_contract_conformance,
)


def test_provider_contract_conformance_matches_declared_support() -> None:
    report = build_provider_contract_conformance_report()

    assert report.passed is True
    assert report.provider_count == 3
    assert report.control_count == 26
    assert report.active_contract_count == 26
    assert report.planned_contract_count == 52
    assert report.failed_contract_count == 0
    assert report.passed_contract_count == 78


def test_provider_contract_conformance_distinguishes_active_and_planned() -> None:
    report = build_provider_contract_conformance_report()
    signals = {signal.provider: signal for signal in report.provider_signals}

    assert signals["azure"].adapter_registered is True
    assert signals["azure"].live_collector_present is True
    assert signals["azure"].collector_tests_present is True
    assert signals["azure"].docs_present is True
    assert signals["azure"].status == "active_ready"

    assert signals["aws"].adapter_registered is False
    assert signals["aws"].live_collector_present is False
    assert signals["aws"].docs_present is True
    assert signals["aws"].status == "planned_ready"

    assert signals["gcp"].adapter_registered is False
    assert signals["gcp"].live_collector_present is False
    assert signals["gcp"].docs_present is True
    assert signals["gcp"].status == "planned_ready"


def test_provider_contract_conformance_dashboard_summary() -> None:
    report = build_provider_contract_conformance_report()
    summary = summarize_provider_contract_conformance(report)

    assert summary["passed"] is True
    assert summary["active_contract_count"] == 26
    assert summary["planned_contract_count"] == 52
    assert summary["failed_contract_count"] == 0
