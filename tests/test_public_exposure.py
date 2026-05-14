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


def test_public_exposure_collects_email_dns_policy_and_security_txt() -> None:
    def lookup(name: str, record_type: str, timeout: float) -> dict:
        records = {
            ("example.com", "TXT"): ["v=spf1 include:_spf.example.net -all"],
            ("_dmarc.example.com", "TXT"): ["v=DMARC1; p=quarantine"],
            ("_mta-sts.example.com", "TXT"): ["v=STSv1; id=20260514"],
            ("_smtp._tls.example.com", "TXT"): ["v=TLSRPTv1; rua=mailto:tls@example.com"],
            ("example.com", "CAA"): ['0 issue "letsencrypt.org"'],
        }
        return {"name": name, "type": record_type, "records": records.get((name, record_type), [])}

    def http_probe(url: str, timeout: float) -> dict:
        if url.endswith("/.well-known/security.txt"):
            return {"url": url, "reachable": True, "status": 200, "headers": {}}
        return {
            "url": url,
            "reachable": True,
            "status": 200,
            "final_url": url,
            "location": "https://example.com",
            "headers": {
                "strict-transport-security": "max-age=31536000",
                "content-security-policy": "default-src 'self'",
                "x-frame-options": "DENY",
                "x-content-type-options": "nosniff",
            },
        }

    report = PublicExposureScanner(
        resolver=lambda host: ["93.184.216.34"],
        http_probe=http_probe,
        tls_probe=lambda host, port, timeout: {
            "available": True,
            "protocol": "TLSv1.3",
            "days_until_expiry": 60,
        },
        dns_record_lookup=lookup,
    ).assess(["example.com"], authorization_confirmed=True)

    target = report["targets"][0]
    assert target["dns_records"]["spf"]["records"] == ["v=spf1 include:_spf.example.net -all"]
    assert target["dns_records"]["dmarc"]["records"] == ["v=DMARC1; p=quarantine"]
    assert target["dns_records"]["mta_sts"]["records"] == ["v=STSv1; id=20260514"]
    assert target["dns_records"]["tls_rpt"]["records"] == ["v=TLSRPTv1; rua=mailto:tls@example.com"]
    assert target["dns_records"]["caa"]["records"] == ['0 issue "letsencrypt.org"']
    assert target["dns_records"]["dkim"]["status"] == "selector_required"
    assert target["security_txt"]["status"] == 200
    assert not any(finding["id"] in {"PE-006", "PE-007", "PE-008", "PE-009"} for finding in report["findings"])


def test_public_exposure_flags_missing_passive_dns_records_and_security_txt() -> None:
    report = PublicExposureScanner(
        resolver=lambda host: ["93.184.216.34"],
        http_probe=lambda url, timeout: {"url": url, "reachable": False, "status": 0, "headers": {}},
        tls_probe=lambda host, port, timeout: {"available": False},
        dns_record_lookup=lambda name, record_type, timeout: {"name": name, "type": record_type, "records": []},
    ).assess(["example.com"], authorization_confirmed=True)

    ids = {finding["id"] for finding in report["findings"]}
    assert {"PE-006", "PE-007", "PE-008", "PE-009"} <= ids


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
