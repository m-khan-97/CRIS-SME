from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

from scripts.lock_dependencies import INPUTS, PROFILES, check, fingerprints


@pytest.fixture
def locked_tree(tmp_path: Path) -> Path:
    for name in [*INPUTS, *(f"requirements/{profile}.txt" for profile in PROFILES)]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n")
    (tmp_path / "requirements/lock-manifest.json").write_text(
        json.dumps({"sha256": fingerprints(tmp_path)})
    )
    return tmp_path


def test_matching_locks_pass(locked_tree: Path) -> None:
    assert check(locked_tree)


@pytest.mark.parametrize("path", [*INPUTS, "requirements/cloud.txt", "requirements/dev.txt"])
def test_changed_inputs_or_locks_fail(locked_tree: Path, path: str) -> None:
    (locked_tree / path).write_text("changed\n")
    assert not check(locked_tree)


def test_missing_lock_fails(locked_tree: Path) -> None:
    (locked_tree / "requirements/runtime.txt").unlink()
    assert not check(locked_tree)


def test_bad_manifest_fails(locked_tree: Path) -> None:
    (locked_tree / "requirements/lock-manifest.json").write_text("invalid")
    assert not check(locked_tree)


def test_container_base_images_are_digest_pinned() -> None:
    dockerfile = Path(__file__).resolve().parents[1] / "Dockerfile"
    images = [line.split()[1] for line in dockerfile.read_text().splitlines()
              if line.startswith("FROM ")]
    assert len(images) == 2
    assert all(re.fullmatch(r"[^\s@]+@sha256:[0-9a-f]{64}", image) for image in images)
