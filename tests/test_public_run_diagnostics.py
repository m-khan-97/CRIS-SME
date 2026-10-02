"""Raw run diagnostics remain local, while API status preserves useful progress."""
import json

import pytest

from cris_sme.api.local_runner import AssessmentRun, LocalAssessmentRunner, create_handler
from cris_sme.api.public_progress import (
    MAX_EVENT_FILE_BYTES, MAX_PUBLIC_EVENTS, PHASE_LABELS, read_public_events,
)
from cris_sme.engine.assessment_runner import AssessmentPhase
from tests.test_local_api_runner import _request_json


SECRET = "Bearer private-token /private/credentials external-id-secret"


def event(**updates):
    return {"sequence": 1, "phase": "collect_evidence", "status": "started",
            "generated_at": "2026-09-28T12:00:00Z", "message": SECRET,
            "detail": {"token": SECRET}, "extra": SECRET, **updates}


def test_public_phase_registry_tracks_runner_enum():
    assert set(PHASE_LABELS) == {phase.value for phase in AssessmentPhase}


@pytest.mark.parametrize("phase", list(PHASE_LABELS))
@pytest.mark.parametrize("status", ["started", "completed"])
def test_event_projection_preserves_progress_not_free_text(tmp_path, phase, status):
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps(event(phase=phase, status=status)))
    original = path.read_bytes()
    result = read_public_events(path)
    assert len(result) == 1
    assert result[0]["phase"] == phase
    assert result[0]["status"] == status
    assert result[0]["detail"] == {}
    assert SECRET not in json.dumps(result)
    assert "extra" not in result[0]
    assert path.read_bytes() == original


@pytest.mark.parametrize("updates", [
    {"phase": SECRET}, {"phase": {}}, {"status": SECRET}, {"status": []},
    {"sequence": True}, {"sequence": SECRET}, {"sequence": 0}, {"sequence": 10001},
    {"generated_at": SECRET}, {"generated_at": "2026-09-28T12:00:00"},
    {"generated_at": None},
])
def test_malformed_event_fields_are_not_reflected(tmp_path, updates):
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps(event(**updates)))
    assert read_public_events(path) == []


def test_partial_bad_and_deep_lines_do_not_hide_valid_events(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text('null\n[]\n' + '[' * 2000 + '0' + ']' * 2000 + '\n'
                    + json.dumps(event()) + '\n{"partial":')
    assert len(read_public_events(path)) == 1


def test_event_count_is_bounded(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text("\n".join(json.dumps(event(sequence=i + 1)) for i in range(MAX_PUBLIC_EVENTS + 10)))
    assert len(read_public_events(path)) == MAX_PUBLIC_EVENTS


def test_oversized_or_linked_event_files_are_not_loaded(tmp_path):
    path = tmp_path / "events.jsonl"
    with path.open("wb") as stream:
        stream.truncate(MAX_EVENT_FILE_BYTES + 1)
    assert read_public_events(path) == []
    path.unlink()
    secret = tmp_path / "private"
    secret.write_text(json.dumps(event()))
    path.symlink_to(secret)
    assert read_public_events(path) == []


@pytest.mark.parametrize("status", ["queued", "running", "completed", "failed"])
def test_run_projection_withholds_diagnostics_without_mutating_storage(tmp_path, status):
    run = AssessmentRun(run_id="safe-id", collector="aws", status=status,
                        output_dir=str(tmp_path), stdout_tail=SECRET, stderr_tail=SECRET,
                        error=SECRET, external_id=SECRET)
    before = run.to_persisted()
    payload = run.to_dict()
    assert SECRET not in json.dumps(payload)
    assert payload["stdout_tail"] == payload["stderr_tail"] == ""
    assert payload["diagnostics_withheld"] is True
    assert bool(payload["error"]) == (status == "failed")
    assert run.to_persisted() == before
    assert before["stderr_tail"] == SECRET
    assert "external_id" not in before


@pytest.mark.parametrize("restored", [False, True])
def test_current_and_historical_status_routes_do_not_disclose_diagnostics(tmp_path, restored):
    path = tmp_path / ".runs" / "run.events.jsonl"
    path.parent.mkdir()
    path.write_text(json.dumps(event()))
    runner = LocalAssessmentRunner(output_dir=tmp_path)
    run = AssessmentRun(run_id="safe-id", collector="aws", status="failed",
                        output_dir=str(tmp_path), events_path=str(path),
                        stdout_tail=SECRET, stderr_tail=SECRET, error=SECRET)
    runner._repository.save(run.to_persisted())
    runner._runs[run.run_id] = run
    if restored:
        runner = LocalAssessmentRunner(output_dir=tmp_path)
    handler = create_handler(runner)
    for route in ("/api/assessments/safe-id", "/api/assessment-runs"):
        payload = _request_json(handler, "GET", route)
        assert SECRET not in json.dumps(payload)
        assert "collect_evidence" in json.dumps(payload)
    assert runner._repository.get("safe-id")["stderr_tail"] == SECRET
