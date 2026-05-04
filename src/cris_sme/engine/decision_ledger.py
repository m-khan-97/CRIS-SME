# Decision Ledger builder for append-only CRIS-SME governance memory.
from __future__ import annotations

import hashlib
from typing import Any

from cris_sme.models.platform import (
    DecisionLedger,
    DecisionLedgerEvent,
    DecisionLedgerEventType,
)


def build_decision_ledger(
    current_report: dict[str, Any],
    history_reports: list[dict[str, Any]],
    *,
    comparison_basis: str = "same_evaluation_mode",
) -> DecisionLedger:
    """Build append-only governance events from the current and previous reports."""
    generated_at = str(current_report.get("generated_at") or "1970-01-01T00:00:00Z")
    run_id = _run_id(current_report)
    current_mode = _classify_evaluation_mode(current_report)
    previous_report = _select_previous_report(
        current_report=current_report,
        history_reports=history_reports,
        comparison_basis=comparison_basis,
    )
    previous_mode = _classify_evaluation_mode(previous_report) if previous_report else None
    previous_run_id = _run_id(previous_report) if previous_report else None
    current_risks = _index_risks(current_report.get("prioritized_risks", []))
    previous_risks = (
        _index_risks(previous_report.get("prioritized_risks", []))
        if previous_report
        else {}
    )

    events: list[DecisionLedgerEvent] = [
        _event(
            event_type=DecisionLedgerEventType.ASSESSMENT_RECORDED,
            event_time=generated_at,
            run_id=run_id,
            summary=(
                "Assessment run recorded with deterministic scoring, evidence lineage, "
                "and lifecycle-aware governance output."
            ),
            metadata={
                "collector_mode": current_report.get("collector_mode"),
                "overall_risk_score": current_report.get("overall_risk_score"),
                "non_compliant_findings": (
                    current_report.get("evaluation_context", {}) or {}
                ).get("non_compliant_findings"),
                "previous_run_id": previous_run_id,
                "current_evaluation_mode": current_mode,
                "previous_evaluation_mode": previous_mode,
                "comparison_basis": comparison_basis,
            },
        )
    ]

    for key, current in sorted(current_risks.items()):
        previous = previous_risks.get(key)
        if previous is None:
            events.append(
                _finding_event(
                    event_type=DecisionLedgerEventType.FINDING_OPENED,
                    event_time=generated_at,
                    run_id=run_id,
                    current=current,
                    previous=None,
                    summary=f"Finding {current.get('control_id')} opened in the current assessment.",
                )
            )
        else:
            events.append(
                _finding_event(
                    event_type=DecisionLedgerEventType.FINDING_RECURRED,
                    event_time=generated_at,
                    run_id=run_id,
                    current=current,
                    previous=previous,
                    summary=f"Finding {current.get('control_id')} recurred from a previous assessment.",
                )
            )
            if _score_changed(current, previous):
                events.append(
                    _finding_event(
                        event_type=DecisionLedgerEventType.SCORE_CHANGED,
                        event_time=generated_at,
                        run_id=run_id,
                        current=current,
                        previous=previous,
                        summary=(
                            f"Finding {current.get('control_id')} score changed from "
                            f"{_safe_score(previous):.2f} to {_safe_score(current):.2f}."
                        ),
                    )
                )
            if _status(current) != _status(previous):
                events.append(
                    _finding_event(
                        event_type=DecisionLedgerEventType.LIFECYCLE_STATUS_CHANGED,
                        event_time=generated_at,
                        run_id=run_id,
                        current=current,
                        previous=previous,
                        summary=(
                            f"Finding {current.get('control_id')} lifecycle status changed "
                            f"from {_status(previous)} to {_status(current)}."
                        ),
                    )
                )

        exception_event = _exception_event_type(current)
        if exception_event is not None:
            events.append(
                _finding_event(
                    event_type=exception_event,
                    event_time=generated_at,
                    run_id=run_id,
                    current=current,
                    previous=previous,
                    summary=_exception_summary(current, exception_event),
                )
            )

    for key, previous in sorted(previous_risks.items()):
        if key in current_risks:
            continue
        events.append(
            _finding_event(
                event_type=DecisionLedgerEventType.FINDING_RESOLVED,
                event_time=generated_at,
                run_id=run_id,
                current=None,
                previous=previous,
                summary=f"Finding {previous.get('control_id')} was not present in the current assessment.",
            )
        )

    return DecisionLedger(
        generated_at=generated_at,
        current_run_id=run_id,
        previous_run_id=previous_run_id,
        current_evaluation_mode=current_mode,
        previous_evaluation_mode=previous_mode,
        comparison_basis=comparison_basis,
        event_count=len(events),
        events=events,
    )


def summarize_decision_ledger(ledger: DecisionLedger) -> dict[str, Any]:
    """Build a compact dashboard/report summary for a Decision Ledger."""
    counts: dict[str, int] = {}
    for event in ledger.events:
        counts[event.event_type.value] = counts.get(event.event_type.value, 0) + 1
    return {
        "ledger_schema_version": ledger.ledger_schema_version,
        "generated_at": ledger.generated_at,
        "current_run_id": ledger.current_run_id,
        "previous_run_id": ledger.previous_run_id,
        "current_evaluation_mode": ledger.current_evaluation_mode,
        "previous_evaluation_mode": ledger.previous_evaluation_mode,
        "comparison_basis": ledger.comparison_basis,
        "event_count": ledger.event_count,
        "event_type_counts": counts,
        "latest_events": [
            event.model_dump()
            for event in ledger.events[:12]
        ],
    }


def _finding_event(
    *,
    event_type: DecisionLedgerEventType,
    event_time: str,
    run_id: str,
    current: dict[str, Any] | None,
    previous: dict[str, Any] | None,
    summary: str,
) -> DecisionLedgerEvent:
    risk = current or previous or {}
    return _event(
        event_type=event_type,
        event_time=event_time,
        run_id=run_id,
        finding_id=str(risk.get("finding_id")) if risk.get("finding_id") else None,
        control_id=str(risk.get("control_id")) if risk.get("control_id") else None,
        provider=str(risk.get("provider")) if risk.get("provider") else None,
        organization=str(risk.get("organization")) if risk.get("organization") else None,
        resource_scope=str(risk.get("resource_scope")) if risk.get("resource_scope") else None,
        previous_score=_safe_score(previous) if previous is not None else None,
        current_score=_safe_score(current) if current is not None else None,
        previous_status=_status(previous) if previous is not None else None,
        current_status=_status(current) if current is not None else None,
        summary=summary,
        evidence_refs=_evidence_refs(risk),
        metadata={
            "priority": risk.get("priority"),
            "evidence_sufficiency": (risk.get("evidence_quality", {}) or {}).get("sufficiency")
            if isinstance(risk.get("evidence_quality", {}), dict)
            else None,
            "exception_id": _exception_id(risk),
        },
    )


def _event(
    *,
    event_type: DecisionLedgerEventType,
    event_time: str,
    run_id: str,
    summary: str,
    finding_id: str | None = None,
    control_id: str | None = None,
    provider: str | None = None,
    organization: str | None = None,
    resource_scope: str | None = None,
    previous_score: float | None = None,
    current_score: float | None = None,
    previous_status: str | None = None,
    current_status: str | None = None,
    evidence_refs: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> DecisionLedgerEvent:
    raw = "|".join(
        [
            event_type.value,
            event_time,
            run_id,
            finding_id or "",
            control_id or "",
            provider or "",
            organization or "",
            resource_scope or "",
            str(previous_score),
            str(current_score),
            previous_status or "",
            current_status or "",
        ]
    )
    event_id = f"led_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:16]}"
    return DecisionLedgerEvent(
        event_id=event_id,
        event_type=event_type,
        event_time=event_time,
        run_id=run_id,
        finding_id=finding_id,
        control_id=control_id,
        provider=provider,
        organization=organization,
        resource_scope=resource_scope,
        previous_score=previous_score,
        current_score=current_score,
        previous_status=previous_status,
        current_status=current_status,
        summary=summary,
        evidence_refs=evidence_refs or [],
        metadata=metadata or {},
    )


def _index_risks(raw_risks: object) -> dict[str, dict[str, Any]]:
    if not isinstance(raw_risks, list):
        return {}
    risks: dict[str, dict[str, Any]] = {}
    for risk in raw_risks:
        if not isinstance(risk, dict):
            continue
        risks[_risk_key(risk)] = risk
    return risks


def _risk_key(risk: dict[str, Any]) -> str:
    return "|".join(
        [
            str(risk.get("control_id", "")).strip(),
            str(risk.get("provider", "azure")).strip().lower(),
            str(risk.get("organization", "")).strip().lower(),
            str(risk.get("resource_scope", "")).strip().lower(),
        ]
    )


def _select_previous_report(
    *,
    current_report: dict[str, Any],
    history_reports: list[dict[str, Any]],
    comparison_basis: str,
) -> dict[str, Any] | None:
    if not history_reports:
        return None

    normalized_basis = comparison_basis.strip().lower()
    if normalized_basis == "latest_any":
        return history_reports[-1]

    current_mode = _classify_evaluation_mode(current_report)
    for report in reversed(history_reports):
        if _classify_evaluation_mode(report) == current_mode:
            return report
    return None


def _classify_evaluation_mode(report: dict[str, Any] | None) -> str:
    """Classify a report into a ledger comparison mode."""
    if report is None:
        return "none"

    dataset = report.get("evaluation_dataset", {})
    source_types = set()
    authorization_bases = set()
    if isinstance(dataset, dict):
        source_types = {
            str(item).strip().lower()
            for item in dataset.get("source_types", [])
            if str(item).strip()
        }
        authorization_bases = {
            str(item).strip().lower()
            for item in dataset.get("authorization_bases", [])
            if str(item).strip()
        }

    details = _collect_organization_details(report)
    profile_sources = {
        str(item.get("profile_source", "")).strip().lower()
        for item in details
        if str(item.get("profile_source", "")).strip()
    }
    detail_source_types = {
        str(item.get("dataset_source_type", "")).strip().lower()
        for item in details
        if str(item.get("dataset_source_type", "")).strip()
    }
    detail_authorization_bases = {
        str(item.get("authorization_basis", "")).strip().lower()
        for item in details
        if str(item.get("authorization_basis", "")).strip()
    }

    all_source_types = source_types | detail_source_types
    all_authorization_bases = authorization_bases | detail_authorization_bases

    if (
        "vulnerable_lab" in all_source_types
        or "intentionally_vulnerable_lab" in all_authorization_bases
    ):
        return "vulnerable_lab"
    if (
        "synthetic_dataset" in all_source_types
        or "synthetic_dataset" in all_authorization_bases
        or "synthetic" in all_source_types
        or "synthetic" in profile_sources
        or report.get("collector_mode") == "mock"
    ):
        return "synthetic_baseline"
    if report.get("collector_mode") == "azure":
        return "live_azure"
    return "other"


def _collect_organization_details(report: dict[str, Any]) -> list[dict[str, Any]]:
    organizations = report.get("organizations", [])
    if not isinstance(organizations, list):
        return []

    details: list[dict[str, Any]] = []
    for organization in organizations:
        if not isinstance(organization, dict):
            continue
        collection_details = organization.get("collection_details", {})
        if isinstance(collection_details, dict):
            details.append(collection_details)
    return details


def _run_id(report: dict[str, Any] | None) -> str | None:
    if report is None:
        return None
    run_metadata = report.get("run_metadata", {})
    if isinstance(run_metadata, dict) and run_metadata.get("run_id"):
        return str(run_metadata["run_id"])
    raw = "|".join(
        [
            str(report.get("collector_mode", "unknown")),
            str(report.get("generated_at", "unknown")),
        ]
    )
    return f"run_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:16]}"


def _safe_score(risk: dict[str, Any] | None) -> float:
    if risk is None:
        return 0.0
    try:
        return round(float(risk.get("score", 0.0)), 2)
    except (TypeError, ValueError):
        return 0.0


def _score_changed(current: dict[str, Any], previous: dict[str, Any]) -> bool:
    return abs(_safe_score(current) - _safe_score(previous)) >= 0.01


def _status(risk: dict[str, Any] | None) -> str:
    if risk is None:
        return "absent"
    lifecycle = risk.get("lifecycle", {})
    if not isinstance(lifecycle, dict):
        return "open"
    return str(lifecycle.get("status", "open"))


def _evidence_refs(risk: dict[str, Any]) -> list[str]:
    trace = risk.get("finding_trace", {})
    if isinstance(trace, dict):
        refs = trace.get("evidence_refs", [])
        if isinstance(refs, list):
            return [str(ref) for ref in refs]
    return []


def _exception_event_type(risk: dict[str, Any]) -> DecisionLedgerEventType | None:
    status = _status(risk)
    if status in {"accepted_risk", "suppressed"}:
        return DecisionLedgerEventType.EXCEPTION_APPLIED
    if status == "expired_exception":
        return DecisionLedgerEventType.EXCEPTION_EXPIRED
    return None


def _exception_id(risk: dict[str, Any]) -> str | None:
    lifecycle = risk.get("lifecycle", {})
    if not isinstance(lifecycle, dict):
        return None
    exception = lifecycle.get("exception", {})
    if not isinstance(exception, dict):
        return None
    value = exception.get("exception_id")
    return str(value) if value else None


def _exception_summary(
    risk: dict[str, Any],
    event_type: DecisionLedgerEventType,
) -> str:
    if event_type == DecisionLedgerEventType.EXCEPTION_EXPIRED:
        return (
            f"Finding {risk.get('control_id')} has an expired exception and is "
            "treated as active risk until renewed."
        )
    return (
        f"Finding {risk.get('control_id')} has an active exception or suppression "
        "record in the current assessment."
    )
