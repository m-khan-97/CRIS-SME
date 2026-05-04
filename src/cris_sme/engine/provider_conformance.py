# Executable provider support conformance checks for CRIS-SME evidence contracts.
from __future__ import annotations

from pathlib import Path

from cris_sme.collectors.providers import get_profile_adapter
from cris_sme.engine.provider_contracts import build_provider_evidence_contract_catalog
from cris_sme.models.platform import (
    ProviderContractConformanceCheck,
    ProviderContractConformanceReport,
    ProviderEvidenceContractCatalog,
    ProviderImplementationSignal,
)


ACTIVE_LIVE_COLLECTORS = frozenset({"azure"})
REPO_ROOT = Path(__file__).resolve().parents[3]
PROVIDER_TEST_FILES = {
    "azure": ("tests/test_provider_adapters.py", "tests/test_azure_collector.py"),
    "aws": ("tests/test_aws_collector.py",),
    "gcp": ("tests/test_gcp_collector.py",),
}
PROVIDER_DOC_FILES = {
    "azure": ("docs/provider-capability-matrix.md", "docs/provider-evidence-contracts.md"),
    "aws": ("docs/provider-capability-matrix.md", "docs/multi-cloud-expansion.md"),
    "gcp": ("docs/provider-capability-matrix.md", "docs/multi-cloud-expansion.md"),
}


def build_provider_contract_conformance_report(
    catalog: ProviderEvidenceContractCatalog | None = None,
) -> ProviderContractConformanceReport:
    """Validate provider evidence contract claims against implementation signals."""
    contract_catalog = catalog or build_provider_evidence_contract_catalog()
    providers = sorted({contract.provider for contract in contract_catalog.contracts})
    provider_signals = {
        provider: _build_provider_signal(provider)
        for provider in providers
    }
    checks = [
        _build_contract_check(contract, provider_signals[contract.provider])
        for contract in contract_catalog.contracts
    ]
    failed_contract_count = sum(1 for check in checks if not check.passed)
    active_contract_count = sum(
        1 for contract in contract_catalog.contracts
        if contract.support_status in {"active", "supported"}
    )
    planned_contract_count = sum(
        1 for contract in contract_catalog.contracts
        if contract.support_status == "planned"
    )

    return ProviderContractConformanceReport(
        policy_pack_version=contract_catalog.policy_pack_version,
        provider_count=contract_catalog.provider_count,
        control_count=contract_catalog.control_count,
        active_contract_count=active_contract_count,
        planned_contract_count=planned_contract_count,
        passed_contract_count=len(checks) - failed_contract_count,
        failed_contract_count=failed_contract_count,
        passed=failed_contract_count == 0,
        provider_signals=list(provider_signals.values()),
        checks=checks,
    )


def summarize_provider_contract_conformance(
    report: ProviderContractConformanceReport | dict[str, object],
) -> dict[str, object]:
    """Build compact conformance metadata for dashboard/API payloads."""
    raw = report if isinstance(report, dict) else report.model_dump()
    return {
        "conformance_schema_version": raw.get("conformance_schema_version"),
        "policy_pack_version": raw.get("policy_pack_version"),
        "passed": bool(raw.get("passed", False)),
        "provider_count": int(raw.get("provider_count", 0)),
        "control_count": int(raw.get("control_count", 0)),
        "active_contract_count": int(raw.get("active_contract_count", 0)),
        "planned_contract_count": int(raw.get("planned_contract_count", 0)),
        "passed_contract_count": int(raw.get("passed_contract_count", 0)),
        "failed_contract_count": int(raw.get("failed_contract_count", 0)),
    }


def _build_provider_signal(provider: str) -> ProviderImplementationSignal:
    adapter_registered = _adapter_registered(provider)
    live_collector_present = provider in ACTIVE_LIVE_COLLECTORS
    collector_tests_present = _any_path_exists(PROVIDER_TEST_FILES.get(provider, ()))
    docs_present = _any_path_exists(PROVIDER_DOC_FILES.get(provider, ()))
    notes: list[str] = []
    if adapter_registered:
        notes.append("Provider adapter is registered for profile normalization.")
    else:
        notes.append("Provider adapter is not registered for active collection.")
    if live_collector_present:
        notes.append("Live collector mode is enabled for this provider.")
    else:
        notes.append("No live collector mode is enabled for this provider.")
    if collector_tests_present:
        notes.append("Provider collector or adapter tests are present.")
    else:
        notes.append("Provider collector tests are not present.")
    if docs_present:
        notes.append("Provider capability documentation is present.")
    else:
        notes.append("Provider capability documentation is not present.")

    if adapter_registered and live_collector_present and collector_tests_present and docs_present:
        status = "active_ready"
    elif adapter_registered or live_collector_present:
        status = "partial"
    else:
        status = "planned_ready"

    return ProviderImplementationSignal(
        provider=provider,
        adapter_registered=adapter_registered,
        live_collector_present=live_collector_present,
        collector_tests_present=collector_tests_present,
        docs_present=docs_present,
        status=status,
        notes=notes,
    )


def _build_contract_check(
    contract: object,
    signal: ProviderImplementationSignal,
) -> ProviderContractConformanceCheck:
    support_status = str(getattr(contract, "support_status"))
    required_signals = _required_signals_for_status(support_status)
    satisfied_signals = [
        name
        for name in required_signals
        if _signal_is_satisfied(name, signal)
    ]
    findings = [
        _finding_for_missing_signal(name, signal.provider, support_status)
        for name in required_signals
        if name not in satisfied_signals
    ]
    return ProviderContractConformanceCheck(
        contract_id=str(getattr(contract, "contract_id")),
        provider=str(getattr(contract, "provider")),
        control_id=str(getattr(contract, "control_id")),
        support_status=support_status,
        passed=not findings,
        required_signals=required_signals,
        satisfied_signals=satisfied_signals,
        findings=findings,
    )


def _required_signals_for_status(support_status: str) -> list[str]:
    if support_status in {"active", "supported"}:
        return [
            "adapter_registered",
            "live_collector_present",
            "collector_tests_present",
            "docs_present",
        ]
    if support_status == "planned":
        return [
            "adapter_not_registered",
            "live_collector_not_present",
            "docs_present",
        ]
    return ["adapter_not_registered", "live_collector_not_present"]


def _signal_is_satisfied(name: str, signal: ProviderImplementationSignal) -> bool:
    if name == "adapter_registered":
        return signal.adapter_registered
    if name == "adapter_not_registered":
        return not signal.adapter_registered
    if name == "live_collector_present":
        return signal.live_collector_present
    if name == "live_collector_not_present":
        return not signal.live_collector_present
    if name == "collector_tests_present":
        return signal.collector_tests_present
    if name == "docs_present":
        return signal.docs_present
    return False


def _finding_for_missing_signal(name: str, provider: str, support_status: str) -> str:
    if name == "adapter_registered":
        return f"{provider} is marked {support_status} but has no registered adapter."
    if name == "adapter_not_registered":
        return f"{provider} is marked {support_status} but an adapter is registered."
    if name == "live_collector_present":
        return f"{provider} is marked {support_status} but has no live collector mode."
    if name == "live_collector_not_present":
        return f"{provider} is marked {support_status} but has an active live collector mode."
    if name == "collector_tests_present":
        return f"{provider} is marked {support_status} but lacks provider collector tests."
    if name == "docs_present":
        return f"{provider} is marked {support_status} but lacks provider documentation."
    return f"{provider} is missing conformance signal {name}."


def _adapter_registered(provider: str) -> bool:
    try:
        get_profile_adapter(provider)
    except ValueError:
        return False
    return True


def _any_path_exists(paths: tuple[str, ...]) -> bool:
    return any((REPO_ROOT / path).exists() for path in paths)
