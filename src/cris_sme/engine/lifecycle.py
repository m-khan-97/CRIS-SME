# Finding lifecycle and exception handling for CRIS-SME decision outputs.
from __future__ import annotations

from datetime import UTC, datetime
import fnmatch
import json
from pathlib import Path
from statistics import mean
from typing import Any

from cris_sme.engine.scoring import CATEGORY_WEIGHTS
from cris_sme.models.finding import FindingCategory
from cris_sme.models.platform import ExceptionRecord, FindingStatus, MuteRule


DEFAULT_EXCEPTION_REGISTRY_PATH = Path("data/finding_exceptions.json")
DEFAULT_MUTE_RULE_REGISTRY_PATH = Path("data/mute_rules.json")


def load_exception_registry(
    path: str | Path = DEFAULT_EXCEPTION_REGISTRY_PATH,
) -> list[ExceptionRecord]:
    """Load approved finding exceptions from the registry file."""
    registry_path = Path(path)
    if not registry_path.exists():
        return []

    raw = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return []
    return [
        ExceptionRecord.model_validate(item)
        for item in raw
        if isinstance(item, dict)
    ]


def load_mute_rules(
    path: str | Path = DEFAULT_MUTE_RULE_REGISTRY_PATH,
) -> list[MuteRule]:
    """Load operational mute rules from the registry file."""
    registry_path = Path(path)
    if not registry_path.exists():
        return []

    raw = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return []
    return [
        MuteRule.model_validate(item)
        for item in raw
        if isinstance(item, dict)
    ]


def enrich_report_finding_lifecycle(
    report: dict[str, Any],
    history_reports: list[dict[str, Any]],
    *,
    exception_registry: list[ExceptionRecord] | None = None,
    mute_rule_registry: list[MuteRule] | None = None,
) -> dict[str, Any]:
    """Attach first-seen/last-seen status lifecycle fields to prioritized findings."""
    prioritized_risks = report.get("prioritized_risks", [])
    if not isinstance(prioritized_risks, list):
        return {
            "status_counts": {},
            "new_findings": 0,
            "existing_findings": 0,
            "exception_applied_count": 0,
            "mute_rule_applied_count": 0,
        }

    generated_at = str(report.get("generated_at", ""))
    history_index = _build_history_index(history_reports)
    exceptions = exception_registry if exception_registry is not None else load_exception_registry()
    mute_rules = mute_rule_registry if mute_rule_registry is not None else load_mute_rules()

    status_counts: dict[str, int] = {}
    new_findings = 0
    existing_findings = 0
    exception_applied_count = 0
    mute_rule_applied_count = 0

    for risk in prioritized_risks:
        if not isinstance(risk, dict):
            continue
        key = _finding_key(risk)
        timeline = history_index.get(key, [])
        first_seen = timeline[0] if timeline else generated_at
        previous_seen = timeline[-1] if timeline else None
        is_new = len(timeline) == 0

        lifecycle_status = FindingStatus.OPEN
        lifecycle_reason = "Active non-compliant finding in current assessment."
        matched_exception = _match_exception(risk, exceptions)
        if matched_exception is not None:
            if _is_expired(matched_exception.expires_at, generated_at):
                lifecycle_status = FindingStatus.EXPIRED_EXCEPTION
                lifecycle_reason = (
                    "Exception exists but is expired; finding is treated as active risk until renewed."
                )
            else:
                lifecycle_status = matched_exception.status
                lifecycle_reason = "Finding lifecycle status set by approved exception record."
                exception_applied_count += 1

        matched_mute_rule = None
        if lifecycle_status != FindingStatus.EXPIRED_EXCEPTION:
            matched_mute_rule = _match_mute_rule(risk, mute_rules, generated_at)
            if matched_mute_rule is not None:
                lifecycle_status = FindingStatus.SUPPRESSED
                lifecycle_reason = "Finding suppressed by an enabled operational mute rule."
                mute_rule_applied_count += 1

        lifecycle = {
            "status": lifecycle_status.value,
            "status_reason": lifecycle_reason,
            "first_seen": first_seen,
            "last_seen": generated_at,
            "previous_seen": previous_seen,
            "is_new": is_new,
            "seen_count": len(timeline) + 1,
            "recurrence_count": len(timeline),
        }
        if matched_exception is not None:
            lifecycle["exception"] = {
                "exception_id": matched_exception.exception_id,
                "approved_by": matched_exception.approved_by,
                "reason": matched_exception.reason,
                "scope": matched_exception.scope,
                "status": matched_exception.status.value,
                "expires_at": matched_exception.expires_at,
                "compensating_control": matched_exception.compensating_control,
            }
        if matched_mute_rule is not None:
            lifecycle["mute_rule"] = {
                "rule_id": matched_mute_rule.rule_id,
                "name": matched_mute_rule.name,
                "reason": matched_mute_rule.reason,
                "created_by": matched_mute_rule.created_by,
                "expires_at": matched_mute_rule.expires_at,
            }
        risk["lifecycle"] = lifecycle

        status_counts[lifecycle_status.value] = status_counts.get(lifecycle_status.value, 0) + 1
        if is_new:
            new_findings += 1
        else:
            existing_findings += 1

    return {
        "status_counts": status_counts,
        "new_findings": new_findings,
        "existing_findings": existing_findings,
        "exception_applied_count": exception_applied_count,
        "exception_registry_count": len(exceptions),
        "mute_rule_applied_count": mute_rule_applied_count,
        "mute_rule_registry_count": len(mute_rules),
    }


EXCLUDED_FROM_SCORING_STATUSES = {
    FindingStatus.SUPPRESSED.value,
    FindingStatus.RESOLVED.value,
    FindingStatus.ACCEPTED_RISK.value,
}


def compute_adjusted_risk_scores(report: dict[str, Any]) -> dict[str, Any]:
    """Recompute risk scores after excluding muted, resolved, or accepted findings.

    Expired exceptions intentionally keep their full score weight so that expiry
    is enforced back into the headline risk posture until the exception is renewed.
    """
    prioritized_risks = report.get("prioritized_risks", [])
    if not isinstance(prioritized_risks, list):
        return {}

    grouped_scores: dict[str, list[float]] = {category.value: [] for category in FindingCategory}
    excluded_count = 0

    for risk in prioritized_risks:
        if not isinstance(risk, dict):
            continue
        status = str(risk.get("lifecycle", {}).get("status", FindingStatus.OPEN.value))
        if status in EXCLUDED_FROM_SCORING_STATUSES:
            excluded_count += 1
            continue
        category = str(risk.get("category", ""))
        score = risk.get("score")
        if category in grouped_scores and isinstance(score, (int, float)):
            grouped_scores[category].append(float(score))

    category_scores = {
        category: round(mean(scores), 2) if scores else 0.0
        for category, scores in grouped_scores.items()
    }

    overall_risk_score = round(
        sum(
            category_scores.get(category.value, 0.0) * weight
            for category, weight in CATEGORY_WEIGHTS.items()
        ),
        2,
    )

    return {
        "overall_risk_score": overall_risk_score,
        "category_scores": category_scores,
        "excluded_finding_count": excluded_count,
    }


def _build_history_index(
    history_reports: list[dict[str, Any]],
) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for historical_report in history_reports:
        generated_at = str(historical_report.get("generated_at", "")).strip()
        risks = historical_report.get("prioritized_risks", [])
        if not generated_at or not isinstance(risks, list):
            continue
        for risk in risks:
            if not isinstance(risk, dict):
                continue
            key = _finding_key(risk)
            index.setdefault(key, []).append(generated_at)
    return {
        key: sorted(set(values))
        for key, values in index.items()
    }


def _finding_key(risk: dict[str, Any]) -> str:
    control_id = str(risk.get("control_id", "")).strip()
    provider = str(risk.get("provider", "azure")).strip().lower()
    organization = str(risk.get("organization", "")).strip().lower()
    resource_scope = str(risk.get("resource_scope", "")).strip().lower()
    return f"{control_id}|{provider}|{organization}|{resource_scope}"


def _match_exception(
    risk: dict[str, Any],
    exceptions: list[ExceptionRecord],
) -> ExceptionRecord | None:
    control_id = str(risk.get("control_id", "")).strip()
    provider = str(risk.get("provider", "azure")).strip().lower()
    resource_scope = str(risk.get("resource_scope", "")).strip().lower()

    for exception in exceptions:
        if exception.control_id != control_id:
            continue
        if exception.provider.strip().lower() != provider:
            continue
        scope = exception.scope.strip().lower()
        if scope not in {"*", "any"} and scope not in resource_scope:
            continue
        return exception
    return None


def _match_mute_rule(
    risk: dict[str, Any],
    mute_rules: list[MuteRule],
    generated_at: str,
) -> MuteRule | None:
    control_id = str(risk.get("control_id", "")).strip()
    provider = str(risk.get("provider", "azure")).strip().lower()
    resource_scope = str(risk.get("resource_scope", "")).strip().lower()
    finding_id = str(risk.get("finding_id", "")).strip()

    for rule in mute_rules:
        if not rule.enabled:
            continue
        if rule.expires_at and _is_expired(rule.expires_at, generated_at):
            continue
        if rule.control_id and rule.control_id != control_id:
            continue
        if rule.provider and rule.provider.strip().lower() != provider:
            continue
        if rule.scope_pattern not in {"*", "any"} and not fnmatch.fnmatch(
            resource_scope, rule.scope_pattern.strip().lower()
        ):
            continue
        if rule.finding_id_pattern and not fnmatch.fnmatch(
            finding_id, rule.finding_id_pattern
        ):
            continue
        return rule
    return None


def _is_expired(expires_at: str, generated_at: str) -> bool:
    expiry = _parse_datetime(expires_at)
    generated = _parse_datetime(generated_at)
    if expiry is None or generated is None:
        return False
    return generated > expiry


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
