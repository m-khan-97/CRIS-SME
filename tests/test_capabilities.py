from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.validate_capabilities import ROOT, validate_manifest


@pytest.fixture
def manifest(tmp_path: Path) -> dict:
    (tmp_path / "evidence.txt").write_text("Original scoped observation", encoding="utf-8")
    return {
        "schema_version": "1.0", "reviewed_on": "2026-09-26",
        "capabilities": [{
            "id": "sample_capability", "title": "Example", "owner": "RE",
            "delivery": "implemented", "scope": "Fixture only",
            "implementation": ["evidence.txt"], "fixture_tests": [],
            "live_observations": [], "independent_reviews": [],
            "limitations": ["Not a live assessment"],
        }],
    }


def record(tmp_path: Path) -> dict:
    return {
        "path": "evidence.txt",
        "sha256": hashlib.sha256((tmp_path / "evidence.txt").read_bytes()).hexdigest(),
        "observed_on": "2026-09-25", "scope": "One account, one control",
        "environment": "controlled fixture", "observer": "Test author",
        "independence": "internal",
    }


def test_repository_manifest_passes() -> None:
    manifest = json.loads((ROOT / "data/capabilities/manifest.json").read_text())
    assert validate_manifest(ROOT, manifest) == []


def test_fixture_does_not_require_live_or_independent_claims(tmp_path: Path, manifest: dict) -> None:
    assert validate_manifest(tmp_path, manifest) == []


@pytest.mark.parametrize("mutation", [
    "unknown_field", "missing_scope", "empty_implementation", "empty_limitations",
    "invalid_date", "unknown_delivery", "duplicate_id", "planned_with_code",
])
def test_invalid_claims_fail(tmp_path: Path, manifest: dict, mutation: str) -> None:
    item = manifest["capabilities"][0]
    if mutation == "unknown_field":
        item["certified"] = True
    elif mutation == "missing_scope":
        del item["scope"]
    elif mutation == "empty_implementation":
        item["implementation"] = []
    elif mutation == "empty_limitations":
        item["limitations"] = []
    elif mutation == "invalid_date":
        manifest["reviewed_on"] = "2026-02-30"
    elif mutation == "unknown_delivery":
        item["delivery"] = "enterprise_ready"
    elif mutation == "duplicate_id":
        manifest["capabilities"].append(deepcopy(item))
    else:
        item["delivery"] = "planned"
    assert validate_manifest(tmp_path, manifest)


@pytest.mark.parametrize("name", ["missing.py", "../outside.py", "/etc/passwd", "https://example.org", "..\\outside.py"])
def test_invalid_evidence_paths_fail(tmp_path: Path, manifest: dict, name: str) -> None:
    manifest["capabilities"][0]["implementation"] = [name]
    assert validate_manifest(tmp_path, manifest)


def test_symlink_escape_fails(tmp_path: Path, manifest: dict) -> None:
    (tmp_path / "outside").symlink_to(ROOT / "README.md")
    manifest["capabilities"][0]["implementation"] = ["outside"]
    assert validate_manifest(tmp_path, manifest)


def test_original_observation_digest_is_checked(tmp_path: Path, manifest: dict) -> None:
    manifest["capabilities"][0]["live_observations"] = [record(tmp_path)]
    assert validate_manifest(tmp_path, manifest) == []
    (tmp_path / "evidence.txt").write_text("Reclassified observation", encoding="utf-8")
    assert "digest mismatch" in " ".join(validate_manifest(tmp_path, manifest))


def test_internal_review_cannot_claim_independence(tmp_path: Path, manifest: dict) -> None:
    evidence = record(tmp_path)
    manifest["capabilities"][0]["independent_reviews"] = [evidence]
    assert "cannot claim independence" in " ".join(validate_manifest(tmp_path, manifest))
    evidence["independence"] = "independent"
    assert validate_manifest(tmp_path, manifest) == []


def test_evidence_cannot_postdate_review(tmp_path: Path, manifest: dict) -> None:
    evidence = record(tmp_path)
    evidence["observed_on"] = "2026-09-27"
    manifest["capabilities"][0]["live_observations"] = [evidence]
    assert "later than manifest review" in " ".join(validate_manifest(tmp_path, manifest))


def test_duplicate_evidence_fails(tmp_path: Path, manifest: dict) -> None:
    evidence = record(tmp_path)
    manifest["capabilities"][0]["live_observations"] = [evidence, deepcopy(evidence)]
    assert "duplicate evidence" in " ".join(validate_manifest(tmp_path, manifest))


@pytest.mark.parametrize("contents", ["{broken", '{"schema_version": "wrong"}'])
def test_cli_fails_for_invalid_input(tmp_path: Path, contents: str) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(contents, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/validate_capabilities.py"), "--manifest", str(path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
