# Tests for scoped public exposure assessment.
from __future__ import annotations

import json

import pytest

from cris_sme.engine.public_exposure import (
    PublicExposureScanner,
    build_public_exposure_markdown,
    normalize_targets,
    write_public_exposure_outputs,
)


def test_normalize_targets_accepts_urls_domains_and_deduplicates() -> None:
    targets = normalize_targets(
        [
            "https://App.Example.com/path",
            "app.example.com",
            "api.example.com",
        ]
    )

    assert [target["host"] for target in targets] == ["app.example.com", "api.example.com"]
    assert targets[0]["scheme_hint"] == "https"


def test_public_exposure_requires_authorization() -> None:
    scanner = PublicExposureScanner()

    with pytest.raises(ValueError, match="authorization_confirmed"):
        scanner.assess(["example.com"], authorization_confirmed=False)


def test_public_exposure_flags_http_without_https_and_missing_headers() -> None:
    def resolver(host: str) -> list[str]:
        assert host == "example.com"
        return ["93.184.216.34"]

    def http_probe(url: str, timeout: float) -> dict:
        if url.startswith("https://"):
            return {"url": url, "reachable": False, "error": "connection refused", "headers": {}}
        return {
            "url": url,
            "reachable": True,
            "status": 200,
            "final_url": url,
            "location": "",
            "headers": {"server": "demo"},
        }

    def tls_probe(host: str, port: int, timeout: float) -> dict:
        return {"host": host, "port": port, "available": False, "error": "connection refused"}

    report = PublicExposureScanner(
        resolver=resolver,
        http_probe=http_probe,
        tls_probe=tls_probe,
    ).assess(["example.com"], authorization_confirmed=True)

    ids = {finding["id"] for finding in report["findings"]}
    assert {"PE-002", "PE-005"} <= ids
    assert report["summary"]["target_count"] == 1
    assert report["summary"]["high_finding_count"] == 1


def test_public_exposure_flags_missing_https_security_headers() -> None:
    def http_probe(url: str, timeout: float) -> dict:
        if url.startswith("https://"):
            return {
                "url": url,
                "reachable": True,
                "status": 200,
                "final_url": url,
                "headers": {"strict-transport-security": "max-age=31536000"},
            }
        return {
            "url": url,
            "reachable": True,
            "status": 301,
            "final_url": "https://secure.example.com",
            "location": "https://secure.example.com",
            "headers": {},
        }

    report = PublicExposureScanner(
        resolver=lambda host: ["93.184.216.34"],
        http_probe=http_probe,
        tls_probe=lambda host, port, timeout: {
            "available": True,
            "protocol": "TLSv1.3",
            "days_until_expiry": 60,
        },
    ).assess(["secure.example.com"], authorization_confirmed=True)

    finding = next(item for item in report["findings"] if item["id"] == "PE-003")
    assert "CSP" in finding["evidence"]["missing_headers"]


def test_public_exposure_excludes_private_targets_by_default() -> None:
    report = PublicExposureScanner(
        resolver=lambda host: ["10.0.0.4"],
        http_probe=lambda url, timeout: {"reachable": True},
        tls_probe=lambda host, port, timeout: {"available": True},
    ).assess(["internal.example.test"], authorization_confirmed=True)

    assert report["findings"][0]["id"] == "PE-000"
    assert report["targets"][0]["https"]["skipped"] is True


def test_write_public_exposure_outputs(tmp_path) -> None:
    report = {
        "generated_at": "2026-05-13T00:00:00Z",
        "scope_note": "Authorised targets only.",
        "summary": {"target_count": 1, "resolved_target_count": 1, "https_available_count": 1, "finding_count": 0},
        "findings": [],
    }

    paths = write_public_exposure_outputs(report, tmp_path)

    assert json.loads((tmp_path / "cris_sme_public_exposure.json").read_text())["summary"]["target_count"] == 1
    assert "No public exposure findings" in build_public_exposure_markdown(report)
    assert paths["markdown"].endswith("cris_sme_public_exposure.md")
