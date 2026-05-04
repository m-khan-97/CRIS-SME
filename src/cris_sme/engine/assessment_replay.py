# Assessment replay and evidence diff utilities for deterministic CRIS-SME runs.
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from cris_sme.controls import (
    evaluate_compute_controls,
    evaluate_data_controls,
    evaluate_governance_controls,
    evaluate_iam_controls,
    evaluate_monitoring_controls,
    evaluate_network_controls,
)
from cris_sme.engine.scoring import ScoringResult, score_findings
from cris_sme.models.cloud_profile import CloudProfile
from cris_sme.models.finding import Finding
from cris_sme.models.platform import (
    AssessmentReplayResult,
    EvidenceDiffResult,
    EvidenceSnapshot,
)
from cris_sme.policies import POLICY_PACK_VERSION


def build_evidence_snapshot(
    *,
    profiles: list[CloudProfile],
    findings: list[Finding],
    collector_mode: str,
    generated_at: str,
    policy_pack_version: str = POLICY_PACK_VERSION,
) -> EvidenceSnapshot:
    """Build a replayable normalized evidence snapshot from an assessment run."""
    profile_payloads = [_canonical_profile(profile) for profile in profiles]
    finding_payloads = [_canonical_finding(finding) for finding in findings]
    profile_sha256 = _sha256_json(profile_payloads)
    finding_sha256 = _sha256_json(finding_payloads)
    snapshot_body = {
        "collector_mode": collector_mode,
        "policy_pack_version": policy_pack_version,
        "profile_sha256": profile_sha256,
        "finding_sha256": finding_sha256,
        "profile_count": len(profile_payloads),
        "finding_count": len(finding_payloads),
    }
    snapshot_sha256 = _sha256_json(snapshot_body)

    return EvidenceSnapshot(
        snapshot_id=f"evs_{snapshot_sha256[:16]}",
        generated_at=generated_at,
        collector_mode=collector_mode,
        policy_pack_version=policy_pack_version,
        profile_count=len(profile_payloads),
        finding_count=len(finding_payloads),
        non_compliant_finding_count=sum(
            1 for finding in findings if not finding.is_compliant
        ),
        providers_in_scope=sorted({profile.provider for profile in profiles}),
        control_ids=sorted({finding.control_id for finding in findings}),
        profile_sha256=profile_sha256,
        finding_sha256=finding_sha256,
        snapshot_sha256=snapshot_sha256,
        profiles=profile_payloads,
        findings=finding_payloads,
        notes=[
            "Snapshot stores normalized profile evidence and deterministic finding inputs.",
            "Replay does not recollect cloud evidence.",
        ],
    )


def replay_evidence_snapshot(
    snapshot: EvidenceSnapshot | dict[str, Any],
) -> AssessmentReplayResult:
    """Replay a saved evidence snapshot through the current deterministic engine."""
    parsed = (
        snapshot
        if isinstance(snapshot, EvidenceSnapshot)
        else EvidenceSnapshot.model_validate(snapshot)
    )
    replayed_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    errors: list[str] = []

    try:
        profiles = [CloudProfile.model_validate(item) for item in parsed.profiles]
        original_findings = [Finding.model_validate(item) for item in parsed.findings]
        replayed_findings = evaluate_profiles(profiles)
        original_score = score_findings(original_findings)
        replayed_score = score_findings(replayed_findings)
    except Exception as exc:  # pragma: no cover - defensive API boundary
        errors.append(str(exc))
        return _failed_replay(parsed, replayed_at, errors)

    replay_profile_sha256 = _sha256_json([_canonical_profile(item) for item in profiles])
    replay_finding_sha256 = _sha256_json(
        [_canonical_finding(item) for item in replayed_findings]
    )
    profile_hash_verified = replay_profile_sha256 == parsed.profile_sha256
    finding_hash_verified = replay_finding_sha256 == parsed.finding_sha256
    category_deltas = _category_score_deltas(original_score, replayed_score)
    overall_delta = round(
        replayed_score.overall_risk_score - original_score.overall_risk_score,
        2,
    )
    policy_same = parsed.policy_pack_version == POLICY_PACK_VERSION
    deterministic_match = (
        profile_hash_verified
        and finding_hash_verified
        and overall_delta == 0
        and original_score.non_compliant_findings == replayed_score.non_compliant_findings
    )

    return AssessmentReplayResult(
        snapshot_id=parsed.snapshot_id,
        replayed_at=replayed_at,
        replayable=not errors,
        deterministic_match=deterministic_match,
        policy_pack_version_at_capture=parsed.policy_pack_version,
        policy_pack_version_at_replay=POLICY_PACK_VERSION,
        collector_mode=parsed.collector_mode,
        profile_hash_verified=profile_hash_verified,
        finding_hash_verified=finding_hash_verified,
        original_profile_sha256=parsed.profile_sha256,
        replay_profile_sha256=replay_profile_sha256,
        original_finding_sha256=parsed.finding_sha256,
        replay_finding_sha256=replay_finding_sha256,
        original_overall_risk_score=original_score.overall_risk_score,
        replayed_overall_risk_score=replayed_score.overall_risk_score,
        overall_risk_delta=overall_delta,
        original_non_compliant_findings=original_score.non_compliant_findings,
        replayed_non_compliant_findings=replayed_score.non_compliant_findings,
        category_score_deltas=category_deltas,
        change_reasons=_replay_change_reasons(
            policy_same=policy_same,
            profile_hash_verified=profile_hash_verified,
            finding_hash_verified=finding_hash_verified,
            overall_delta=overall_delta,
            category_deltas=category_deltas,
        ),
        errors=errors,
    )


def build_evidence_diff_result(
    current: EvidenceSnapshot | dict[str, Any],
    previous: EvidenceSnapshot | dict[str, Any] | None,
) -> EvidenceDiffResult:
    """Compare two snapshots and classify whether evidence, policy, or collector changed."""
    current_snapshot = (
        current if isinstance(current, EvidenceSnapshot) else EvidenceSnapshot.model_validate(current)
    )
    if previous is None:
        return EvidenceDiffResult(
            current_snapshot_id=current_snapshot.snapshot_id,
            previous_snapshot_id=None,
            comparable=False,
            evidence_changed=False,
            policy_pack_changed=False,
            collector_mode_changed=False,
            score_delta_reason="No previous evidence snapshot is available for comparison.",
        )

    previous_snapshot = (
        previous
        if isinstance(previous, EvidenceSnapshot)
        else EvidenceSnapshot.model_validate(previous)
    )
    evidence_changed = (
        current_snapshot.profile_sha256 != previous_snapshot.profile_sha256
        or current_snapshot.finding_sha256 != previous_snapshot.finding_sha256
    )
    policy_pack_changed = (
        current_snapshot.policy_pack_version != previous_snapshot.policy_pack_version
    )
    collector_mode_changed = (
        current_snapshot.collector_mode != previous_snapshot.collector_mode
    )
    current_controls = set(current_snapshot.control_ids)
    previous_controls = set(previous_snapshot.control_ids)

    return EvidenceDiffResult(
        current_snapshot_id=current_snapshot.snapshot_id,
        previous_snapshot_id=previous_snapshot.snapshot_id,
        comparable=True,
        evidence_changed=evidence_changed,
        policy_pack_changed=policy_pack_changed,
        collector_mode_changed=collector_mode_changed,
        profile_count_delta=current_snapshot.profile_count - previous_snapshot.profile_count,
        finding_count_delta=current_snapshot.finding_count - previous_snapshot.finding_count,
        non_compliant_finding_count_delta=(
            current_snapshot.non_compliant_finding_count
            - previous_snapshot.non_compliant_finding_count
        ),
        added_control_ids=sorted(current_controls - previous_controls),
        removed_control_ids=sorted(previous_controls - current_controls),
        score_delta_reason=_score_delta_reason(
            evidence_changed=evidence_changed,
            policy_pack_changed=policy_pack_changed,
            collector_mode_changed=collector_mode_changed,
        ),
    )


def build_report_replay_summary(
    *,
    current_snapshot: EvidenceSnapshot,
    previous_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build report-ready replay and diff metadata."""
    previous_snapshot_raw = (
        previous_report.get("evidence_snapshot")
        if isinstance(previous_report, dict)
        else None
    )
    replay = replay_evidence_snapshot(current_snapshot)
    diff = build_evidence_diff_result(current_snapshot, previous_snapshot_raw)
    return {
        "replay": replay.model_dump(mode="json"),
        "evidence_diff": diff.model_dump(mode="json"),
    }


def evaluate_profiles(profiles: list[CloudProfile]) -> list[Finding]:
    """Evaluate all deterministic CRIS-SME controls for normalized profiles."""
    return [
        *evaluate_iam_controls(profiles),
        *evaluate_network_controls(profiles),
        *evaluate_data_controls(profiles),
        *evaluate_monitoring_controls(profiles),
        *evaluate_compute_controls(profiles),
        *evaluate_governance_controls(profiles),
    ]


def _failed_replay(
    snapshot: EvidenceSnapshot,
    replayed_at: str,
    errors: list[str],
) -> AssessmentReplayResult:
    return AssessmentReplayResult(
        snapshot_id=snapshot.snapshot_id,
        replayed_at=replayed_at,
        replayable=False,
        deterministic_match=False,
        policy_pack_version_at_capture=snapshot.policy_pack_version,
        policy_pack_version_at_replay=POLICY_PACK_VERSION,
        collector_mode=snapshot.collector_mode,
        profile_hash_verified=False,
        finding_hash_verified=False,
        original_profile_sha256=snapshot.profile_sha256,
        replay_profile_sha256="0" * 64,
        original_finding_sha256=snapshot.finding_sha256,
        replay_finding_sha256="0" * 64,
        original_overall_risk_score=0.0,
        replayed_overall_risk_score=0.0,
        overall_risk_delta=0.0,
        original_non_compliant_findings=snapshot.non_compliant_finding_count,
        replayed_non_compliant_findings=0,
        category_score_deltas={},
        change_reasons=["Snapshot could not be replayed."],
        errors=errors,
    )


def _canonical_profile(profile: CloudProfile) -> dict[str, Any]:
    return profile.model_dump(mode="json")


def _canonical_finding(finding: Finding) -> dict[str, Any]:
    return finding.model_dump(mode="json")


def _sha256_json(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _category_score_deltas(
    original_score: ScoringResult,
    replayed_score: ScoringResult,
) -> dict[str, float]:
    categories = set(original_score.category_scores) | set(replayed_score.category_scores)
    return {
        category: round(
            replayed_score.category_scores.get(category, 0.0)
            - original_score.category_scores.get(category, 0.0),
            2,
        )
        for category in sorted(categories)
    }


def _replay_change_reasons(
    *,
    policy_same: bool,
    profile_hash_verified: bool,
    finding_hash_verified: bool,
    overall_delta: float,
    category_deltas: dict[str, float],
) -> list[str]:
    reasons: list[str] = []
    if policy_same and profile_hash_verified and finding_hash_verified and overall_delta == 0:
        reasons.append("Replay matched the captured deterministic decision inputs.")
    if not policy_same:
        reasons.append("Policy pack version changed between capture and replay.")
    if not profile_hash_verified:
        reasons.append("Normalized profile evidence hash changed during replay.")
    if not finding_hash_verified:
        reasons.append("Control finding hash changed during replay.")
    if overall_delta != 0 or any(value != 0 for value in category_deltas.values()):
        reasons.append("Risk score changed under replay.")
    return reasons or ["Replay completed with no classified change reason."]


def _score_delta_reason(
    *,
    evidence_changed: bool,
    policy_pack_changed: bool,
    collector_mode_changed: bool,
) -> str:
    if evidence_changed and policy_pack_changed:
        return "Evidence and policy pack both changed; score movement cannot be attributed to one source alone."
    if evidence_changed:
        return "Evidence changed while policy pack stayed the same; score movement is evidence-driven."
    if policy_pack_changed:
        return "Policy pack changed while evidence stayed the same; score movement is policy-driven."
    if collector_mode_changed:
        return "Collector mode changed without evidence hash movement; review collection metadata."
    return "Evidence and policy pack are unchanged; score movement should be zero under deterministic replay."
