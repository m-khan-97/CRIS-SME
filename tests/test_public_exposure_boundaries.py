"""Outbound scope regressions; only loopback test servers are contacted."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from cris_sme.engine.public_exposure import (
    PublicExposureScanner,
    PublicExposureSettings,
    is_private_address,
    probe_http,
)


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308, 404, 200])
def test_http_records_first_response_without_redirects_or_environment_proxy(monkeypatch, status):
    paths = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            paths.append(self.path)
            self.send_response(status)
            self.send_header("Location", "/not-authorised")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("http_proxy", "http://127.0.0.1:1")
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("no_proxy", "")
    monkeypatch.setenv("NO_PROXY", "")
    url = f"http://127.0.0.1:{server.server_port}/original"
    try:
        result = probe_http(url, 2, allow_private_targets=True)
        assert result["reachable"] is True
        assert result["status"] == status
        assert result["final_url"] == url
        assert result["location"] == "/not-authorised"
        assert paths == ["/original"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com", "data:text/plain,test"])
def test_http_rejects_non_web_schemes(url):
    with pytest.raises(ValueError, match="Only HTTP"):
        probe_http(url, 1)


@pytest.mark.parametrize("address", ["100.64.0.1", "169.254.169.254", "::1", "invalid", "10.0.0.1"])
def test_non_global_or_invalid_addresses_are_excluded(address):
    assert is_private_address(address)


@pytest.mark.parametrize("addresses", [[], ["invalid"], ["93.184.216.34", "100.64.0.1"]])
def test_unresolved_and_excluded_targets_never_probe(addresses):
    def forbidden(*args):
        pytest.fail("Unvalidated target reached an outbound probe")

    scanner = PublicExposureScanner(
        settings=PublicExposureSettings(scan_common_ports=True),
        resolver=lambda host: addresses,
        http_probe=forbidden,
        tls_probe=forbidden,
        port_probe=forbidden,
        dns_record_lookup=forbidden,
    )
    report = scanner.assess(["example.com"], authorization_confirmed=True)
    assert report["targets"][0]["http"]["skipped"]
    assert report["findings"][0]["id"] == ("PE-001" if not addresses else "PE-000")


def test_dns_failure_never_probes_even_in_private_mode():
    def unavailable(host):
        raise OSError("DNS unavailable")

    def forbidden(*args):
        pytest.fail("DNS failure must not trigger probes")

    report = PublicExposureScanner(
        settings=PublicExposureSettings(allow_private_targets=True),
        resolver=unavailable, http_probe=forbidden, tls_probe=forbidden,
        dns_record_lookup=forbidden,
    ).assess(["example.com"], authorization_confirmed=True)
    assert report["findings"][0]["evidence"]["dns_error"] == "DNS unavailable"


def test_redirect_is_not_evidence_that_security_txt_was_retrieved():
    report = PublicExposureScanner(
        resolver=lambda host: ["93.184.216.34"],
        http_probe=lambda url, timeout: {
            "reachable": True, "status": 302, "headers": {},
            "location": "https://elsewhere.example/security.txt",
        },
        tls_probe=lambda *args: {"available": False},
        dns_record_lookup=lambda *args: {"records": []},
    ).assess(["example.com"], authorization_confirmed=True)
    assert "PE-009" in {finding["id"] for finding in report["findings"]}
