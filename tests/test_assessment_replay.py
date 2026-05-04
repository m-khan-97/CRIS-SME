# Tests for CRIS-SME assessment replay and evidence diff behavior.
from cris_sme.collectors.mock_collector import MockCollector
from cris_sme.engine.assessment_replay import (
    build_evidence_diff_result,
    build_evidence_snapshot,
    build_report_replay_summary,
    evaluate_profiles,
    replay_evidence_snapshot,
)
from cris_sme.policies import POLICY_PACK_VERSION


def test_evidence_snapshot_replays_deterministically() -> None:
    profiles = MockCollector().collect_profiles()
    findings = evaluate_profiles(profiles)
    snapshot = build_evidence_snapshot(
        profiles=profiles,
        findings=findings,
        collector_mode="mock",
        generated_at="2026-05-04T00:00:00Z",
    )

    replay = replay_evidence_snapshot(snapshot)

    assert snapshot.snapshot_id.startswith("evs_")
    assert snapshot.profile_count == len(profiles)
    assert snapshot.finding_count == len(findings)
    assert snapshot.policy_pack_version == POLICY_PACK_VERSION
    assert replay.replayable is True
    assert replay.deterministic_match is True
    assert replay.profile_hash_verified is True
    assert replay.finding_hash_verified is True
    assert replay.overall_risk_delta == 0


def test_evidence_diff_classifies_evidence_driven_change() -> None:
    profiles = MockCollector().collect_profiles()
    current_findings = evaluate_profiles(profiles)
    previous_profiles = profiles[:-1]
    previous_findings = evaluate_profiles(previous_profiles)

    current = build_evidence_snapshot(
        profiles=profiles,
        findings=current_findings,
        collector_mode="mock",
        generated_at="2026-05-04T00:00:00Z",
    )
    previous = build_evidence_snapshot(
        profiles=previous_profiles,
        findings=previous_findings,
        collector_mode="mock",
        generated_at="2026-05-03T00:00:00Z",
    )

    diff = build_evidence_diff_result(current, previous)

    assert diff.comparable is True
    assert diff.evidence_changed is True
    assert diff.policy_pack_changed is False
    assert diff.profile_count_delta == 1
    assert diff.score_delta_reason == (
        "Evidence changed while policy pack stayed the same; "
        "score movement is evidence-driven."
    )


def test_report_replay_summary_handles_missing_previous_snapshot() -> None:
    profiles = MockCollector().collect_profiles()
    findings = evaluate_profiles(profiles)
    snapshot = build_evidence_snapshot(
        profiles=profiles,
        findings=findings,
        collector_mode="mock",
        generated_at="2026-05-04T00:00:00Z",
    )

    summary = build_report_replay_summary(current_snapshot=snapshot)

    assert summary["replay"]["deterministic_match"] is True
    assert summary["evidence_diff"]["comparable"] is False
    assert summary["evidence_diff"]["previous_snapshot_id"] is None
