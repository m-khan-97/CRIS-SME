"""Bound local API reads even when file metadata becomes stale."""
import json
import os
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote

import pytest

from cris_sme.api.artifact_access import (
    ArtifactTooLarge, MAX_ARTIFACT_BYTES, MAX_REPORT_BYTES, read_regular_file,
)
from cris_sme.api.local_runner import LocalAssessmentRunner, create_handler
from tests.test_local_api_runner import _request_raw


@pytest.mark.parametrize("size", [0, 3, 4])
def test_reader_accepts_files_up_to_exact_limit(tmp_path, size):
    (tmp_path / "report").write_bytes(b"x" * size)
    assert read_regular_file(tmp_path, Path("report"), max_bytes=4) == b"x" * size


@pytest.mark.parametrize("limit", [0, -1, True, 1.5, None])
def test_invalid_read_limits_fail_before_file_access(tmp_path, limit):
    with pytest.raises(ValueError, match="positive integer"):
        read_regular_file(tmp_path, Path("missing"), max_bytes=limit)


def test_oversized_file_is_rejected_before_read(tmp_path, monkeypatch):
    (tmp_path / "report").write_bytes(b"12345")
    original = os.fdopen

    class Guard:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def fileno(self):
            return self.stream.fileno()

        def read(self, *args):
            pytest.fail("Oversized file was read before rejection")

    monkeypatch.setattr(os, "fdopen", lambda *args: Guard(original(*args)))
    with pytest.raises(ArtifactTooLarge):
        read_regular_file(tmp_path, Path("report"), max_bytes=4)


def test_stale_small_stat_cannot_bypass_bounded_read(tmp_path, monkeypatch):
    (tmp_path / "report").write_bytes(b"12345678")
    original_stat = os.fstat
    original_open = os.fdopen
    requested_sizes = []

    def small_stat(descriptor):
        return SimpleNamespace(st_mode=original_stat(descriptor).st_mode, st_size=1)

    class Spy:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def fileno(self):
            return self.stream.fileno()

        def read(self, size):
            requested_sizes.append(size)
            return self.stream.read(size)

    monkeypatch.setattr(os, "fstat", small_stat)
    monkeypatch.setattr(os, "fdopen", lambda *args: Spy(original_open(*args)))
    with pytest.raises(ArtifactTooLarge):
        read_regular_file(tmp_path, Path("report"), max_bytes=4)
    assert requested_sizes == [5]


@pytest.mark.parametrize("route", ["outputs", "artifact"])
def test_oversized_allowed_download_returns_413(tmp_path, route):
    target = tmp_path / "cris_sme_summary.txt"
    with target.open("wb") as stream:
        stream.truncate(MAX_ARTIFACT_BYTES + 1)
    handler = create_handler(LocalAssessmentRunner(output_dir=tmp_path))
    path = f"/outputs/{target.name}" if route == "outputs" else f"/api/report-artifact?path={quote(str(target))}"
    body = _request_raw(handler, "GET", path, expected_status=413)
    assert b"size limit" in body
    assert len(body) < 1024


def test_oversized_history_is_skipped_before_json_decoding(tmp_path, monkeypatch):
    target = tmp_path / "cris_sme_report.json"
    with target.open("wb") as stream:
        stream.truncate(MAX_REPORT_BYTES + 1)
    runner = LocalAssessmentRunner(output_dir=tmp_path)

    def forbidden(*args, **kwargs):
        pytest.fail("Oversized report reached the JSON decoder")

    monkeypatch.setattr("cris_sme.api.local_runner.json.loads", forbidden)
    assert runner.assessment_history() == []


@pytest.mark.parametrize("payload", [
    {"run_metadata": "invalid"}, {"run_metadata": ["invalid"]},
    {"organizations": {"0": {"organization_name": "invalid"}}},
    {"organizations": "invalid"}, ["not a report"],
])
def test_malformed_metadata_does_not_break_history(tmp_path, payload):
    (tmp_path / "cris_sme_report.json").write_text(json.dumps(payload))
    assert LocalAssessmentRunner(output_dir=tmp_path).assessment_history() == []


def test_deeply_nested_report_is_skipped_without_crashing(tmp_path):
    (tmp_path / "cris_sme_report.json").write_text('[' * 2000 + '0' + ']' * 2000)
    assert LocalAssessmentRunner(output_dir=tmp_path).assessment_history() == []


def test_valid_history_survives_an_oversized_current_report(tmp_path):
    with (tmp_path / "cris_sme_report.json").open("wb") as stream:
        stream.truncate(MAX_REPORT_BYTES + 1)
    history = tmp_path / "history"
    history.mkdir()
    report = {"run_metadata": {"run_id": "valid"}}
    (history / "cris_sme_report_20260928T120000Z.json").write_text(json.dumps(report))
    runner = LocalAssessmentRunner(output_dir=tmp_path)
    assert [entry["run_id"] for entry in runner.assessment_history()] == ["valid"]
    assert runner.assessment_report("valid") == report


def test_selected_report_rechecks_size_after_indexing(tmp_path, monkeypatch):
    target = tmp_path / "cris_sme_report.json"
    with target.open("wb") as stream:
        stream.truncate(MAX_REPORT_BYTES + 1)
    runner = LocalAssessmentRunner(output_dir=tmp_path)
    monkeypatch.setattr("cris_sme.api.local_runner._report_index",
                        lambda root, **kwargs: [({"report_id": "replaced"}, target)])
    assert runner.assessment_report("replaced") is None
