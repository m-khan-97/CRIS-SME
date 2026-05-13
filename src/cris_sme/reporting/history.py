# Report history utilities for archiving CRIS-SME assessment snapshots over time.
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ── Drift analysis constants ──────────────────────────────────────────────────
_MIN_RUNS_FOR_TREND = 3   # minimum history depth for a meaningful slope
_DAYS_PER_WEEK = 7.0


def archive_report_snapshot(
    report: dict[str, Any],
    output_dir: str | Path,
    *,
    timestamp: datetime | None = None,
) -> Path:
    """Persist a timestamped JSON snapshot for later trend and comparison analysis."""
    snapshot_time = timestamp or datetime.now(UTC)
    history_dir = Path(output_dir) / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    stamp = snapshot_time.strftime("%Y%m%dT%H%M%SZ")
    snapshot_path = history_dir / f"cris_sme_report_{stamp}.json"
    snapshot_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return snapshot_path


def load_report_history(history_dir: str | Path) -> list[dict[str, Any]]:
    """Load archived CRIS-SME report snapshots ordered by capture time."""
    directory = Path(history_dir)
    if not directory.exists():
        return []

    reports: list[dict[str, Any]] = []
    for path in sorted(directory.glob("cris_sme_report_*.json")):
        try:
            reports.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return reports


def build_history_comparison(
    reports: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a compact comparison between the current and previous archived runs."""
    if not reports:
        return {
            "history_count": 0,
            "latest_generated_at": None,
            "previous_generated_at": None,
            "overall_risk_delta": None,
            "non_compliant_findings_delta": None,
            "category_score_deltas": {},
            "current_collector_mode": None,
            "previous_collector_mode": None,
        }

    current = reports[-1]
    previous = reports[-2] if len(reports) >= 2 else None
    previous_distinct_mode = _find_previous_distinct_mode_report(reports)
    current_categories = current.get("category_scores", {})
    previous_categories = previous.get("category_scores", {}) if previous else {}

    category_deltas: dict[str, float] = {}
    if isinstance(current_categories, dict):
        for category, value in current_categories.items():
            current_score = _safe_float(value)
            previous_score = _safe_float(previous_categories.get(category))
            category_deltas[str(category)] = round(current_score - previous_score, 2)

    current_context = current.get("evaluation_context", {})
    previous_context = previous.get("evaluation_context", {}) if previous else {}
    trend_series = _build_overall_trend_series(reports)
    domain_trend = _build_domain_trend_series(reports)
    current_risk_index = _index_risks_by_key(current.get("prioritized_risks", []))
    previous_risk_index = _index_risks_by_key(
        previous.get("prioritized_risks", [])
    ) if previous else {}
    new_keys = set(current_risk_index) - set(previous_risk_index)
    resolved_keys = set(previous_risk_index) - set(current_risk_index)
    recurring_regressions = [
        key
        for key in (set(current_risk_index) & set(previous_risk_index))
        if _safe_float(current_risk_index[key].get("score"))
        >= _safe_float(previous_risk_index[key].get("score"))
    ]

    comparison = {
        "history_count": len(reports),
        "latest_generated_at": current.get("generated_at"),
        "previous_generated_at": previous.get("generated_at") if previous else None,
        "overall_risk_delta": (
            round(
                _safe_float(current.get("overall_risk_score"))
                - _safe_float(previous.get("overall_risk_score")),
                2,
            )
            if previous
            else None
        ),
        "non_compliant_findings_delta": (
            int(current_context.get("non_compliant_findings", 0))
            - int(previous_context.get("non_compliant_findings", 0))
            if previous
            else None
        ),
        "category_score_deltas": category_deltas,
        "current_collector_mode": current.get("collector_mode"),
        "previous_collector_mode": previous.get("collector_mode") if previous else None,
        "previous_distinct_mode": (
            previous_distinct_mode.get("collector_mode")
            if previous_distinct_mode
            else None
        ),
        "previous_distinct_generated_at": (
            previous_distinct_mode.get("generated_at")
            if previous_distinct_mode
            else None
        ),
        "overall_risk_delta_vs_distinct_mode": (
            round(
                _safe_float(current.get("overall_risk_score"))
                - _safe_float(previous_distinct_mode.get("overall_risk_score")),
                2,
            )
            if previous_distinct_mode
            else None
        ),
        "control_score_deltas": _build_control_score_deltas(
            current,
            previous,
        ),
        "control_score_deltas_vs_distinct_mode": _build_control_score_deltas(
            current,
            previous_distinct_mode,
        ),
        "overall_trend": trend_series,
        "domain_trend": domain_trend,
        "new_findings_count": len(new_keys),
        "resolved_findings_count": len(resolved_keys),
        "recurring_regression_count": len(recurring_regressions),
        "new_findings": [_compact_key_details(key) for key in sorted(new_keys)[:30]],
        "resolved_findings": [_compact_key_details(key) for key in sorted(resolved_keys)[:30]],
        "recurring_regressions": [
            {
                **_compact_key_details(key),
                "current_score": round(_safe_float(current_risk_index[key].get("score")), 2),
                "previous_score": round(_safe_float(previous_risk_index[key].get("score")), 2),
            }
            for key in sorted(recurring_regressions)[:30]
        ],
        "priority_distribution_trend": _build_priority_distribution_trend(reports),
        "framework_readiness_trend": _build_framework_readiness_trend(reports),
    }
    return comparison


def build_evaluation_mode_summary(
    reports: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize the latest archived report for each major evaluation mode."""
    if not reports:
        return {"mode_count": 0, "modes": []}

    latest_by_mode: dict[str, dict[str, Any]] = {}
    for report in reports:
        latest_by_mode[_classify_evaluation_mode(report)] = report

    modes: list[dict[str, Any]] = []
    for mode_key in ("synthetic_baseline", "live_azure", "vulnerable_lab", "other"):
        report = latest_by_mode.get(mode_key)
        if report is None:
            continue
        context = report.get("evaluation_context", {})
        modes.append(
            {
                "mode_key": mode_key,
                "label": _mode_label(mode_key),
                "evidence_class": _evidence_class(mode_key),
                "generated_at": report.get("generated_at"),
                "collector_mode": report.get("collector_mode"),
                "overall_risk_score": round(
                    _safe_float(report.get("overall_risk_score")),
                    2,
                ),
                "generated_findings": int(context.get("generated_findings", 0))
                if isinstance(context, dict)
                else 0,
                "non_compliant_findings": int(
                    context.get("non_compliant_findings", 0)
                )
                if isinstance(context, dict)
                else 0,
                "category_scores": {
                    str(category): round(_safe_float(score), 2)
                    for category, score in (
                        report.get("category_scores", {}) or {}
                    ).items()
                }
                if isinstance(report.get("category_scores"), dict)
                else {},
            }
        )

    return {"mode_count": len(modes), "modes": modes}


def _safe_float(value: Any) -> float:
    """Return a float-like value or zero when conversion fails."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _classify_evaluation_mode(report: dict[str, Any]) -> str:
    """Classify a report into a paper-facing evaluation mode."""
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
        or "synthetic" in profile_sources
        or report.get("collector_mode") == "mock"
    ):
        return "synthetic_baseline"

    if report.get("collector_mode") == "azure":
        return "live_azure"

    return "other"


def _collect_organization_details(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect per-organization collection detail dictionaries from a report."""
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


def _mode_label(mode_key: str) -> str:
    """Return the paper-facing label for an evaluation mode."""
    labels = {
        "synthetic_baseline": "Synthetic Baseline",
        "live_azure": "Live Azure Case Study",
        "vulnerable_lab": "AzureGoat Vulnerable Lab",
        "other": "Other Assessment Mode",
    }
    return labels.get(mode_key, "Other Assessment Mode")


def _evidence_class(mode_key: str) -> str:
    """Return a short evidence-class description for an evaluation mode."""
    classes = {
        "synthetic_baseline": "Controlled synthetic profiles",
        "live_azure": "Authorized live Azure evidence",
        "vulnerable_lab": "Intentionally vulnerable lab evidence",
        "other": "Other archived assessment evidence",
    }
    return classes.get(mode_key, "Other archived assessment evidence")


def _find_previous_distinct_mode_report(
    reports: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return the most recent archived report with a different collector mode."""
    if len(reports) < 2:
        return None

    current_mode = reports[-1].get("collector_mode")
    for report in reversed(reports[:-1]):
        if report.get("collector_mode") != current_mode:
            return report
    return None


def _build_control_score_deltas(
    current: dict[str, Any],
    previous: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Return control-level score changes between two reports."""
    if previous is None:
        return []

    current_risks = _index_risks_by_control_id(current.get("prioritized_risks", []))
    previous_risks = _index_risks_by_control_id(previous.get("prioritized_risks", []))

    deltas: list[dict[str, Any]] = []
    for control_id, risk in current_risks.items():
        previous_risk = previous_risks.get(control_id)
        current_score = _safe_float(risk.get("score"))
        previous_score = _safe_float(previous_risk.get("score")) if previous_risk else 0.0
        deltas.append(
            {
                "control_id": control_id,
                "title": risk.get("title"),
                "category": risk.get("category"),
                "current_score": round(current_score, 2),
                "previous_score": round(previous_score, 2),
                "delta": round(current_score - previous_score, 2),
                "current_priority": risk.get("priority"),
                "previous_priority": previous_risk.get("priority") if previous_risk else None,
            }
        )

    return sorted(
        deltas,
        key=lambda item: abs(_safe_float(item.get("delta"))),
        reverse=True,
    )


def _index_risks_by_control_id(risks: Any) -> dict[str, dict[str, Any]]:
    """Index prioritized risks by control identifier."""
    indexed: dict[str, dict[str, Any]] = {}
    if not isinstance(risks, list):
        return indexed

    for risk in risks:
        if not isinstance(risk, dict):
            continue
        control_id = str(risk.get("control_id", "")).strip()
        if control_id:
            indexed[control_id] = risk
    return indexed


def _index_risks_by_key(risks: Any) -> dict[str, dict[str, Any]]:
    """Index prioritized risks by a stable control/organization/scope composite key."""
    indexed: dict[str, dict[str, Any]] = {}
    if not isinstance(risks, list):
        return indexed
    for risk in risks:
        if not isinstance(risk, dict):
            continue
        control_id = str(risk.get("control_id", "")).strip()
        provider = str(risk.get("provider", "azure")).strip().lower()
        organization = str(risk.get("organization", "")).strip().lower()
        scope = str(risk.get("resource_scope", "")).strip().lower()
        if not control_id:
            continue
        indexed[f"{control_id}|{provider}|{organization}|{scope}"] = risk
    return indexed


def _compact_key_details(key: str) -> dict[str, str]:
    """Convert a composite risk key into a compact serializable detail object."""
    control_id, provider, organization, scope = (key.split("|", 3) + ["", "", "", ""])[:4]
    return {
        "control_id": control_id,
        "provider": provider,
        "organization": organization,
        "resource_scope": scope,
    }


def _build_overall_trend_series(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return run-by-run overall score trend data."""
    return [
        {
            "generated_at": report.get("generated_at"),
            "collector_mode": report.get("collector_mode"),
            "overall_risk_score": round(_safe_float(report.get("overall_risk_score")), 2),
            "non_compliant_findings": int(
                (report.get("evaluation_context", {}) or {}).get("non_compliant_findings", 0)
            ),
        }
        for report in reports
    ]


def _build_domain_trend_series(reports: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Return per-domain score trend records keyed by category name."""
    categories: dict[str, list[dict[str, Any]]] = {}
    for report in reports:
        generated_at = report.get("generated_at")
        category_scores = report.get("category_scores", {})
        if not isinstance(category_scores, dict):
            continue
        for category, score in category_scores.items():
            categories.setdefault(str(category), []).append(
                {
                    "generated_at": generated_at,
                    "score": round(_safe_float(score), 2),
                }
            )
    return categories


def _build_priority_distribution_trend(
    reports: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build trend data for priority-band distributions across runs."""
    trend: list[dict[str, Any]] = []
    for report in reports:
        priorities = {"Immediate": 0, "High": 0, "Planned": 0, "Monitor": 0}
        risks = report.get("prioritized_risks", [])
        if isinstance(risks, list):
            for risk in risks:
                if not isinstance(risk, dict):
                    continue
                label = str(risk.get("priority", "Monitor"))
                priorities[label] = priorities.get(label, 0) + 1
        trend.append(
            {
                "generated_at": report.get("generated_at"),
                "collector_mode": report.get("collector_mode"),
                "distribution": priorities,
            }
        )
    return trend


def build_risk_drift_analysis(
    reports: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute longitudinal risk drift, velocity, and control stability from N history runs.

    Returns a structured dict suitable for inclusion in the JSON report and paper.
    Requires at least three runs to produce a meaningful trend; returns a skeleton
    with status='insufficient_history' for fewer runs.
    """
    if len(reports) < _MIN_RUNS_FOR_TREND:
        return {
            "status": "insufficient_history",
            "minimum_runs_required": _MIN_RUNS_FOR_TREND,
            "available_runs": len(reports),
            "note": (
                f"Risk drift analysis requires at least {_MIN_RUNS_FOR_TREND} "
                "historical snapshots. Run more assessments to activate trend fitting."
            ),
        }

    overall_scores = [_safe_float(r.get("overall_risk_score")) for r in reports]
    timestamps = [_parse_iso(r.get("generated_at")) for r in reports]

    # Overall risk velocity (risk-points per week, positive = worsening)
    overall_slope_per_run = _linear_slope(list(range(len(overall_scores))), overall_scores)
    overall_velocity_weekly = _slope_per_week(overall_slope_per_run, timestamps)

    # Direction label
    direction = _velocity_label(overall_velocity_weekly)

    # Per-category slopes
    category_slopes: dict[str, dict[str, Any]] = {}
    all_categories: set[str] = set()
    for report in reports:
        all_categories.update((report.get("category_scores") or {}).keys())

    for category in sorted(all_categories):
        cat_scores = [
            _safe_float((report.get("category_scores") or {}).get(category))
            for report in reports
        ]
        cat_slope_per_run = _linear_slope(list(range(len(cat_scores))), cat_scores)
        cat_velocity_weekly = _slope_per_week(cat_slope_per_run, timestamps)
        category_slopes[str(category)] = {
            "slope_per_run": round(cat_slope_per_run, 4),
            "velocity_per_week": round(cat_velocity_weekly, 3),
            "direction": _velocity_label(cat_velocity_weekly),
            "first_score": round(cat_scores[0], 2),
            "latest_score": round(cat_scores[-1], 2),
            "change_total": round(cat_scores[-1] - cat_scores[0], 2),
        }

    # Fastest deteriorating category
    worst_category = max(
        category_slopes,
        key=lambda k: category_slopes[k]["velocity_per_week"],
        default=None,
    )

    # Control stability index: fraction of runs each control was non-compliant
    control_appearances: dict[str, int] = {}
    control_non_compliant: dict[str, int] = {}
    for report in reports:
        risks = report.get("prioritized_risks", [])
        seen_controls_this_run: set[str] = set()
        for risk in risks if isinstance(risks, list) else []:
            if not isinstance(risk, dict):
                continue
            control_id = str(risk.get("control_id", "")).strip()
            if not control_id or control_id in seen_controls_this_run:
                continue
            seen_controls_this_run.add(control_id)
            control_appearances[control_id] = control_appearances.get(control_id, 0) + 1
            control_non_compliant[control_id] = control_non_compliant.get(control_id, 0) + 1

    total_runs = len(reports)
    control_stability: list[dict[str, Any]] = []
    for control_id in sorted(control_appearances, key=lambda k: -control_non_compliant.get(k, 0)):
        non_compliant_count = control_non_compliant.get(control_id, 0)
        stability_index = round(non_compliant_count / total_runs, 3)
        control_stability.append(
            {
                "control_id": control_id,
                "non_compliant_run_count": non_compliant_count,
                "total_runs": total_runs,
                "stability_index": stability_index,
                "persistence_label": _persistence_label(stability_index),
            }
        )

    # Persistent controls (always non-compliant) — highest remediation priority
    persistent_controls = [c for c in control_stability if c["stability_index"] == 1.0]

    # Intermittent controls (some runs compliant, some not) — possible false negatives
    intermittent_controls = [
        c for c in control_stability
        if 0.0 < c["stability_index"] < 1.0
    ]

    return {
        "status": "available",
        "run_count": total_runs,
        "first_run_at": reports[0].get("generated_at"),
        "latest_run_at": reports[-1].get("generated_at"),
        "overall_risk": {
            "first_score": round(overall_scores[0], 2),
            "latest_score": round(overall_scores[-1], 2),
            "change_total": round(overall_scores[-1] - overall_scores[0], 2),
            "slope_per_run": round(overall_slope_per_run, 4),
            "velocity_per_week": round(overall_velocity_weekly, 3),
            "direction": direction,
            "direction_note": _velocity_note(direction, overall_velocity_weekly),
        },
        "category_drift": category_slopes,
        "fastest_deteriorating_category": worst_category,
        "control_stability": control_stability[:30],
        "persistent_control_count": len(persistent_controls),
        "persistent_controls": [c["control_id"] for c in persistent_controls],
        "intermittent_control_count": len(intermittent_controls),
        "method": (
            "Ordinary least-squares linear regression on run-indexed risk scores. "
            "Weekly velocity derived from timestamp intervals. "
            "Control stability index = non-compliant runs / total runs (0=always ok, 1=always failing)."
        ),
    }


def _linear_slope(x: list[float], y: list[float]) -> float:
    """Return the OLS slope of y ~ x. Returns 0.0 for degenerate inputs."""
    n = len(x)
    if n < 2:
        return 0.0
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    denominator = sum((x[i] - mean_x) ** 2 for i in range(n))
    if denominator == 0.0:
        return 0.0
    return numerator / denominator


def _slope_per_week(slope_per_run: float, timestamps: list[datetime | None]) -> float:
    """Convert per-run slope to per-week slope using actual timestamp intervals."""
    valid_ts = [ts for ts in timestamps if ts is not None]
    if len(valid_ts) < 2:
        return slope_per_run

    total_days = (valid_ts[-1] - valid_ts[0]).total_seconds() / 86400.0
    if total_days <= 0.0:
        return slope_per_run

    runs_per_week = ((len(valid_ts) - 1) / total_days) * _DAYS_PER_WEEK
    if runs_per_week <= 0.0:
        return slope_per_run

    return slope_per_run * runs_per_week


def _parse_iso(value: Any) -> datetime | None:
    """Parse an ISO 8601 timestamp into an aware datetime."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _velocity_label(velocity_per_week: float) -> str:
    if velocity_per_week > 1.5:
        return "rapidly_worsening"
    if velocity_per_week > 0.3:
        return "worsening"
    if velocity_per_week < -1.5:
        return "rapidly_improving"
    if velocity_per_week < -0.3:
        return "improving"
    return "stable"


def _velocity_note(direction: str, velocity: float) -> str:
    v = abs(round(velocity, 2))
    if direction == "rapidly_worsening":
        return f"Risk score rising at approximately {v} points per week. Urgent remediation review recommended."
    if direction == "worsening":
        return f"Risk score rising at approximately {v} points per week."
    if direction == "rapidly_improving":
        return f"Risk score falling at approximately {v} points per week. Remediation effort is measurably reducing posture risk."
    if direction == "improving":
        return f"Risk score falling at approximately {v} points per week."
    return "Risk score is stable across recent assessment runs."


def _persistence_label(stability_index: float) -> str:
    if stability_index == 1.0:
        return "persistent"
    if stability_index >= 0.75:
        return "frequent"
    if stability_index >= 0.5:
        return "intermittent"
    if stability_index > 0.0:
        return "occasional"
    return "resolved"


def _build_framework_readiness_trend(
    reports: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build trend records for UK-readiness and insurance-readiness outputs."""
    trend: list[dict[str, Any]] = []
    for report in reports:
        readiness = report.get("cyber_essentials_readiness", {})
        insurance = report.get("cyber_insurance_evidence", {})
        insurance_summary = (
            insurance.get("readiness_summary", {})
            if isinstance(insurance, dict)
            else {}
        )
        trend.append(
            {
                "generated_at": report.get("generated_at"),
                "cyber_essentials_score": round(
                    _safe_float(
                        readiness.get("overall_readiness_score")
                        if isinstance(readiness, dict)
                        else 0.0
                    ),
                    2,
                ),
                "insurance_readiness_score": round(
                    _safe_float(
                        insurance_summary.get("readiness_score")
                        if isinstance(insurance_summary, dict)
                        else 0.0
                    ),
                    2,
                ),
            }
        )
    return trend
