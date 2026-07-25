# Tests for the structured CRIS-SME assessment runner.
from cris_sme.collectors.mock_collector import MockCollector
from cris_sme.engine.assessment_runner import (
    AssessmentEvent,
    AssessmentEventStatus,
    AssessmentPhase,
    AssessmentRunner,
)


def test_assessment_runner_emits_core_phase_events() -> None:
    emitted_events: list[AssessmentEvent] = []

    result = AssessmentRunner(
        collector_mode="mock",
        profile_collector=MockCollector().collect_profiles,
        event_handler=emitted_events.append,
    ).run()

    assert result.collector_mode == "mock"
    assert result.profiles
    assert result.findings
    assert result.resource_context.assets
    assert result.resource_context.evidence_records
    assert result.resource_context.finding_asset_links
    assert all(finding.asset_ids for finding in result.findings)
    assert all(finding.evidence_ids for finding in result.findings)
    assert result.scoring_result.total_findings == len(result.findings)
    assert result.compliance_result.mapped_findings
    assert emitted_events == result.events
    assert [event.sequence for event in result.events] == list(range(1, 11))
    assert [(event.phase, event.status) for event in result.events] == [
        (AssessmentPhase.COLLECT_EVIDENCE, AssessmentEventStatus.STARTED),
        (AssessmentPhase.COLLECT_EVIDENCE, AssessmentEventStatus.COMPLETED),
        (AssessmentPhase.EVALUATE_CONTROLS, AssessmentEventStatus.STARTED),
        (AssessmentPhase.EVALUATE_CONTROLS, AssessmentEventStatus.COMPLETED),
        (AssessmentPhase.SCORE_FINDINGS, AssessmentEventStatus.STARTED),
        (AssessmentPhase.SCORE_FINDINGS, AssessmentEventStatus.COMPLETED),
        (AssessmentPhase.MAP_COMPLIANCE, AssessmentEventStatus.STARTED),
        (AssessmentPhase.MAP_COMPLIANCE, AssessmentEventStatus.COMPLETED),
        (AssessmentPhase.ASSESS_EVIDENCE_SUFFICIENCY, AssessmentEventStatus.STARTED),
        (AssessmentPhase.ASSESS_EVIDENCE_SUFFICIENCY, AssessmentEventStatus.COMPLETED),
    ]
    assert result.evidence_sufficiency.sufficiency_counts
    assert sum(result.evidence_sufficiency.sufficiency_counts.values()) == len(
        result.scoring_result.prioritized_findings
    )


def test_assessment_runner_can_scope_to_metadata_v2_controls() -> None:
    result = AssessmentRunner(
        collector_mode="mock",
        profile_collector=MockCollector().collect_profiles,
        control_ids=["IAM-001", "NET-001"],
    ).run()

    assert result.control_selection.registry_filtered is True
    assert result.control_selection.selected_control_ids == ["IAM-001", "NET-001"]
    assert result.control_selection.selected_domains == ["IAM", "Network"]
    assert result.findings
    assert result.resource_context.finding_asset_links
    assert {finding.control_id for finding in result.findings}.issubset(
        {"IAM-001", "NET-001"}
    )
    assert result.scoring_result.total_findings == len(result.findings)
    assert result.events[2].detail["registry_filtered"] is True
    assert result.events[3].detail["finding_count"] == len(result.findings)


def test_assessment_runner_rejects_unknown_scoped_controls() -> None:
    runner = AssessmentRunner(
        collector_mode="mock",
        profile_collector=MockCollector().collect_profiles,
        control_ids=["NOPE-999"],
    )

    try:
        runner.run()
    except KeyError as exc:
        assert "NOPE-999" in str(exc)
    else:  # pragma: no cover - keeps failure readable without pytest import
        raise AssertionError("Expected unknown control selection to fail.")
