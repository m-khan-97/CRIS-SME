from email.message import Message
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from scripts.dependency_license_inventory import npm_inventory, python_inventory


def test_python_retains_expression_and_legacy_metadata() -> None:
    info = Message()
    info["Name"] = "example"
    info["License-Expression"] = "MIT OR Apache-2.0"
    info["License"] = "Legacy notice"
    info["Classifier"] = "License :: OSI Approved :: MIT License"
    info["Classifier"] = "Programming Language :: Python"
    item = python_inventory([SimpleNamespace(metadata=info, version="1.0")])[0]
    assert item["license_expression"] == "MIT OR Apache-2.0"
    assert item["legacy_license"] == "Legacy notice"
    assert len(item["license_classifiers"]) == 1
    assert item["needs_review"] is False


def test_python_does_not_infer_spdx_from_legacy() -> None:
    info = Message()
    info["Name"] = "legacy"
    info["License"] = "BSD"
    item = python_inventory([SimpleNamespace(metadata=info, version="2.0")])[0]
    assert item["needs_review"] is True
    assert item["license_expression"] is None


def test_npm_includes_nested_optional_and_development_records() -> None:
    result = npm_inventory({"lockfileVersion": 3, "packages": {
        "": {"name": "root"},
        "node_modules/a": {"version": "1.0", "license": "MIT", "dev": True},
        "node_modules/a/node_modules/@scope/b": {"version": "2.0", "optional": True},
    }})
    assert len(result) == 2
    assert result[0]["development"] is True
    assert result[1]["name"] == "@scope/b"
    assert result[1]["optional"] is True
    assert result[1]["needs_review"] is True


@pytest.mark.parametrize("license_value", [None, "", "UNKNOWN", "UNLICENSED", "SEE LICENSE IN LICENSE.txt"])
def test_npm_unclear_declarations_require_review(license_value: str | None) -> None:
    result = npm_inventory({"lockfileVersion": 3, "packages": {
        "node_modules/a": {"version": "1", "license": license_value},
    }})
    assert result[0]["needs_review"] is True


@pytest.mark.parametrize("lock", [
    {}, {"lockfileVersion": 1, "packages": {}},
    {"lockfileVersion": 3, "packages": {"node_modules/a": {"link": True}}},
    {"lockfileVersion": 3, "packages": {"node_modules/a": {"version": "1", "license": {"type": "MIT"}}}},
])
def test_unsupported_lock_records_fail(lock: dict) -> None:
    with pytest.raises(ValueError):
        npm_inventory(lock)


def test_cli_records_lock_digest_without_absolute_source_path(tmp_path: Path) -> None:
    lock = tmp_path / "package-lock.json"
    lock.write_text(json.dumps({"lockfileVersion": 3, "packages": {
        "node_modules/a": {"version": "1", "license": "MIT"},
    }}))
    output = tmp_path / "report.json"
    script = Path(__file__).resolve().parents[1] / "scripts/dependency_license_inventory.py"
    subprocess.run([sys.executable, str(script), "--ecosystem", "npm", "--lock", str(lock),
                    "--output", str(output)], check=True)
    report = json.loads(output.read_text())
    assert report["package_count"] == 1
    assert len(report["lock_sha256"]) == 64
    assert str(tmp_path) not in output.read_text()
