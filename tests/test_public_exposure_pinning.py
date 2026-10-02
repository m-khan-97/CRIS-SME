"""Pinned probe transport tests. No external network targets are contacted."""
import socket
import ssl
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from cris_sme.engine import public_exposure as exposure


def no_dns(*args, **kwargs):
    pytest.fail("Pinned connection must not perform a second DNS lookup")


@pytest.mark.parametrize("addresses", [(), ("invalid",), ("93.184.216.34", "127.0.0.1"),
                                       ("169.254.169.254",), ("::ffff:127.0.0.1",),
                                       ("100.64.0.1",), ("fe80::1%eth0",)])
@pytest.mark.parametrize("kind", ["http", "tls", "ports"])
def test_all_probe_entrypoints_reject_unapproved_addresses(monkeypatch, addresses, kind):
    monkeypatch.setattr(exposure, "_connect_addresses", no_dns)
    if kind == "http":
        probe = lambda: exposure.probe_http("https://example.com", 1, addresses=addresses)
    elif kind == "tls":
        probe = lambda: exposure.probe_tls("example.com", 443, 1, addresses=addresses)
    else:
        probe = lambda: exposure.probe_common_ports("example.com", [22], 1, addresses=addresses)
    with pytest.raises(ValueError):
        probe()


@pytest.mark.parametrize("address,family,destination", [
    ("93.184.216.34", socket.AF_INET, ("93.184.216.34", 443)),
    ("2606:4700:4700::1111", socket.AF_INET6, ("2606:4700:4700::1111", 443, 0, 0)),
])
def test_numeric_connector_does_not_resolve(monkeypatch, address, family, destination):
    calls = []

    class Socket:
        def settimeout(self, value):
            assert value > 0

        def connect(self, target):
            calls.append(target)

    sock = Socket()

    def factory(actual_family, kind):
        assert actual_family == family
        assert kind == socket.SOCK_STREAM
        return sock

    monkeypatch.setattr(socket, "getaddrinfo", no_dns)
    monkeypatch.setattr(socket, "socket", factory)
    assert exposure._connect_addresses((address,), 443, 1) is sock
    assert calls == [destination]


def test_failed_address_falls_back_only_to_approved_set_and_closes(monkeypatch):
    sockets = []
    destinations = []

    class Socket:
        closed = False

        def __init__(self, *args):
            sockets.append(self)

        def settimeout(self, value):
            pass

        def connect(self, destination):
            destinations.append(destination)
            if len(destinations) == 1:
                raise ConnectionRefusedError("fixture")

        def close(self):
            self.closed = True

    monkeypatch.setattr(socket, "socket", Socket)
    monkeypatch.setattr(socket, "getaddrinfo", no_dns)
    result = exposure._connect_addresses(("93.184.216.34", "1.1.1.1"), 443, 1)
    assert sockets[0].closed
    assert result is sockets[1]
    assert destinations == [("93.184.216.34", 443), ("1.1.1.1", 443)]


def test_exhausted_pinned_addresses_fail_without_hostname_fallback(monkeypatch):
    closed = []

    class Socket:
        def __init__(self, *args):
            pass

        def settimeout(self, value):
            pass

        def connect(self, target):
            raise ConnectionRefusedError("fixture")

        def close(self):
            closed.append(True)

    monkeypatch.setattr(socket, "socket", Socket)
    monkeypatch.setattr(socket, "getaddrinfo", no_dns)
    with pytest.raises(ConnectionRefusedError):
        exposure._connect_addresses(("1.1.1.1", "93.184.216.34"), 443, 1)
    assert len(closed) == 2


def test_connection_deadline_stops_before_socket_creation(monkeypatch):
    clock = iter([0.0, 2.0])
    monkeypatch.setattr(exposure.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(socket, "socket", no_dns)
    with pytest.raises(TimeoutError):
        exposure._connect_addresses(("1.1.1.1",), 443, 1)


def test_ports_connect_only_to_pinned_addresses(monkeypatch):
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    monkeypatch.setattr(socket, "getaddrinfo", no_dns)
    try:
        result = exposure.probe_common_ports("authorised.test", [port], 1,
                                            addresses=("127.0.0.1",), allow_private_targets=True)
        assert result["open_ports"] == [port]
    finally:
        listener.close()


@pytest.mark.parametrize("addresses", [("invalid",), ("fe80::1%eth0",)])
def test_lab_mode_still_rejects_invalid_or_scoped_addresses(monkeypatch, addresses):
    monkeypatch.setattr(exposure, "_connect_addresses", no_dns)
    with pytest.raises(ValueError):
        exposure.probe_http("http://authorised.test", 1, addresses=addresses,
                            allow_private_targets=True)


def test_direct_probe_resolves_once_and_never_uses_rebound_answer(monkeypatch):
    resolutions = []
    destinations = []

    def resolve(host):
        resolutions.append(host)
        return ["1.1.1.1"] if len(resolutions) == 1 else ["169.254.169.254"]

    class Socket:
        def __init__(self, *args):
            pass

        def settimeout(self, value):
            pass

        def connect(self, destination):
            destinations.append(destination)
            raise ConnectionRefusedError("fixture")

        def close(self):
            pass

    monkeypatch.setattr(exposure, "resolve_host", resolve)
    monkeypatch.setattr(socket, "socket", Socket)
    exposure.probe_common_ports("authorised.test", [22, 443], 1)
    assert resolutions == ["authorised.test"]
    assert sorted(destinations) == [("1.1.1.1", 22), ("1.1.1.1", 443)]


@pytest.mark.parametrize("url", ["https://user:secret@example.com", "https:///missing"])
def test_invalid_authority_is_rejected_before_resolution(monkeypatch, url):
    monkeypatch.setattr(exposure, "resolve_host", no_dns)
    with pytest.raises(ValueError):
        exposure.probe_http(url, 1)


def test_scanner_passes_original_dns_snapshot_to_every_native_probe(monkeypatch):
    calls = []
    resolutions = []

    def resolver(host):
        resolutions.append(host)
        return ["93.184.216.34"] if len(resolutions) == 1 else ["169.254.169.254"]

    def probe(*args, **kwargs):
        calls.append((args, kwargs))
        return {"reachable": False, "available": False}

    monkeypatch.setattr(exposure, "probe_http", probe)
    monkeypatch.setattr(exposure, "probe_tls", probe)
    monkeypatch.setattr(exposure, "probe_common_ports", probe)
    exposure.PublicExposureScanner(
        settings=exposure.PublicExposureSettings(scan_common_ports=True),
        resolver=resolver, dns_record_lookup=lambda *args: {"records": []},
    ).assess(["example.com"], authorization_confirmed=True)
    assert resolutions == ["example.com"]
    assert len(calls) == 5
    assert all(kwargs == {"addresses": ("93.184.216.34",), "allow_private_targets": False}
               for _, kwargs in calls)


@pytest.fixture
def tls_endpoint(tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "authorised.test")])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(days=1))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName("authorised.test")]), False)
            .sign(key, hashes.SHA256()))
    cert_path = tmp_path / "cert.pem"
    key_path = tmp_path / "key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                         serialization.PrivateFormat.PKCS8,
                                         serialization.NoEncryption()))
    observed = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            observed.append((self.headers["Host"], self.path))
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    context.set_servername_callback(lambda sock, host, ctx: observed.append(host))
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port, cert_path, observed
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_https_pins_socket_but_preserves_host_sni_and_certificate_validation(monkeypatch, tls_endpoint):
    port, cert_path, observed = tls_endpoint
    create_context = ssl.create_default_context
    monkeypatch.setattr(ssl, "create_default_context", lambda: create_context(cafile=str(cert_path)))
    monkeypatch.setattr(socket, "getaddrinfo", no_dns)
    result = exposure.probe_http(f"https://authorised.test:{port}/evidence?q=1", 2,
                                 addresses=("127.0.0.1",), allow_private_targets=True)
    assert result["status"] == 200
    assert observed == ["authorised.test", (f"authorised.test:{port}", "/evidence?q=1")]
    with pytest.raises(ssl.SSLCertVerificationError):
        exposure.probe_http(f"https://wrong.test:{port}", 2,
                            addresses=("127.0.0.1",), allow_private_targets=True)


def test_tls_metadata_and_deprecated_checks_share_pinned_addresses(monkeypatch, tls_endpoint):
    port, cert_path, observed = tls_endpoint
    create_context = ssl.create_default_context
    monkeypatch.setattr(ssl, "create_default_context", lambda: create_context(cafile=str(cert_path)))
    monkeypatch.setattr(socket, "getaddrinfo", no_dns)
    # Empty version list avoids platform-specific legacy OpenSSL support in this real TLS test.
    monkeypatch.setattr(exposure, "DEPRECATED_TLS_VERSIONS", [])
    result = exposure.probe_tls("authorised.test", port, 2,
                               addresses=("127.0.0.1",), allow_private_targets=True)
    assert result["available"]
    assert observed == ["authorised.test"]


def test_deprecated_tls_uses_pinned_connector_and_original_sni(monkeypatch):
    calls = []
    class Socket:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class Context:
        def __init__(self, *args):
            pass

        def wrap_socket(self, sock, *, server_hostname):
            assert server_hostname == "authorised.test"
            return sock

    def connect(addresses, port, timeout):
        calls.append((addresses, port, timeout))
        return Socket()

    monkeypatch.setattr(ssl, "SSLContext", Context)
    monkeypatch.setattr(exposure, "_connect_addresses", connect)
    monkeypatch.setattr(socket, "getaddrinfo", no_dns)
    states = exposure._probe_deprecated_tls_versions("authorised.test", 443, 1, ("1.1.1.1",))
    assert calls == [(("1.1.1.1",), 443, 1)] * 2
    assert set(states.values()) == {"supported"}
