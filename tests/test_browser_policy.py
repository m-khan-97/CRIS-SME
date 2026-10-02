from email.message import Message
from io import BytesIO
from types import SimpleNamespace

import pytest

from cris_sme.api.browser_policy import BrowserRequestPolicy, DEFAULT_ALLOWED_ORIGINS
from cris_sme.api.local_runner import create_handler


def headers(*pairs: tuple[str, str]) -> Message:
    message = Message()
    for name, value in pairs:
        message[name] = value
    return message


@pytest.mark.parametrize("origin", DEFAULT_ALLOWED_ORIGINS)
def test_default_origins_are_accepted(origin):
    assert BrowserRequestPolicy().rejection(headers(("Host", "localhost:8787"), ("Origin", origin))) is None


@pytest.mark.parametrize("host", ["localhost", "LOCALHOST:8080", "127.0.0.1:8787", "[::1]:8787"])
def test_local_hosts_are_accepted(host):
    assert BrowserRequestPolicy().rejection(headers(("Host", host))) is None


@pytest.mark.parametrize("host", ["localhost.evil.test", "evil.test", "localhost@evil.test", "localhost/path",
    "localhost:99999", "localhost:", "[::1]evil", "127.0.0.1,evil.test", "127.1", "localhost.", ""])
def test_host_bypasses_are_rejected(host):
    assert BrowserRequestPolicy().rejection(headers(("Host", host)))


@pytest.mark.parametrize("origin", ["null", "*", "https://evil.test", "http://localhost:5174",
    "http://localhost:5173/", "http://localhost:5173.evil.test", "http://localhost:5173 https://evil.test"])
def test_unapproved_origins_are_rejected(origin):
    assert BrowserRequestPolicy().rejection(headers(("Host", "localhost"), ("Origin", origin)))[0] == 403


def test_duplicate_and_missing_headers_fail_closed():
    policy = BrowserRequestPolicy()
    assert policy.rejection(headers())[0] == 400
    assert policy.rejection(headers(("Host", "localhost"), ("Host", "localhost")))[0] == 400
    assert policy.rejection(headers(("Host", "localhost"), ("Origin", "null"), ("Origin", "null")))[0] == 400
    assert policy.rejection(headers(("Host", "localhost"), ("Sec-Fetch-Site", "cross-site")))[0] == 403


@pytest.mark.parametrize("origin", ["*", "null", "file://localhost", "https://test.invalid/path",
    "https://test.invalid?query", "https://test.invalid#fragment", "https://user@test.invalid"])
def test_invalid_origin_configuration_fails(origin):
    with pytest.raises(ValueError):
        BrowserRequestPolicy(allowed_origins=(origin,))


@pytest.mark.parametrize("host", ["*", "http://localhost", "localhost:8787", "[::1]evil"])
def test_invalid_host_configuration_fails(host):
    with pytest.raises(ValueError):
        BrowserRequestPolicy(allowed_hosts=(host,))


def test_explicit_policy_replaces_defaults():
    policy = BrowserRequestPolicy(allowed_hosts=("private.example",), allowed_origins=("https://console.example",))
    assert policy.rejection(headers(("Host", "private.example:443"), ("Origin", "https://console.example"))) is None
    assert policy.rejection(headers(("Host", "localhost")))
    assert policy.rejection(headers(("Host", "private.example"), ("Origin", "http://localhost:5173")))


class Socket:
    def __init__(self, raw):
        self.input = BytesIO(raw)
        self.output = BytesIO()
        self.timeout = None

    def settimeout(self, timeout):
        self.timeout = timeout

    def gettimeout(self):
        return self.timeout

    def makefile(self, mode, *args, **kwargs):
        return self.input if "r" in mode else self.output

    def sendall(self, value):
        self.output.write(value)


def request(runner, method, path, extra=""):
    socket = Socket((f"{method} {path} HTTP/1.1\r\nHost: localhost:8787\r\n"
                     f"{extra}Content-Length: 2\r\nContent-Type: application/json\r\n\r\n{{}}").encode())
    create_handler(runner)(socket, ("127.0.0.1", 12345), object())
    return socket.output.getvalue().split(b"\r\n\r\n", 1)


@pytest.mark.parametrize("method,path", [("GET", "/api/environment/aws"), ("GET", "/outputs/secret.json"),
    ("POST", "/api/assessments/aws"), ("POST", "/api/assessments/azure"),
    ("POST", "/api/public-exposure"), ("POST", "/api/environment/aws/validate-role"), ("OPTIONS", "/health")])
def test_rejected_origin_never_dispatches_route(method, path):
    # No runner methods exist: reaching a route would fail the test.
    response, body = request(SimpleNamespace(), method, path, "Origin: https://evil.test\r\n")
    assert b" 403 " in response.splitlines()[0]
    assert b"Access-Control-Allow-Origin" not in response
    assert b"Origin is not allowed" in body


@pytest.mark.parametrize("method,path", [("GET", "/health"), ("OPTIONS", "/api/assessments/aws"),
    ("GET", "/outputs/cris_sme_report.json")])
def test_successful_responses_echo_only_approved_origin(tmp_path, method, path):
    (tmp_path / "cris_sme_report.json").write_text('{"ok":true}')
    response, _ = request(SimpleNamespace(output_dir=tmp_path, latest_output_dir=lambda: tmp_path), method, path,
                          "Origin: http://localhost:5173\r\n")
    assert b" 200 " in response.splitlines()[0]
    assert b"Access-Control-Allow-Origin: http://localhost:5173" in response
    assert b"Access-Control-Allow-Origin: *" not in response
    assert b"Vary: Origin" in response


def test_cli_request_without_origin_gets_no_cors_permission():
    response, _ = request(SimpleNamespace(), "GET", "/health")
    assert b" 200 " in response.splitlines()[0]
    assert b"Access-Control-Allow-Origin" not in response


def test_policy_on_real_loopback_http_connection():
    from http.client import HTTPConnection
    from http.server import ThreadingHTTPServer
    from threading import Thread

    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(SimpleNamespace()))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    try:
        connection.request("GET", "/health", headers={"Origin": "http://localhost:5173"})
        response = connection.getresponse()
        assert response.status == 200
        assert response.getheader("Access-Control-Allow-Origin") == "http://localhost:5173"
        response.read()
        connection.request("POST", "/api/assessments/aws", body=b"{}",
                           headers={"Origin": "https://evil.test", "Content-Type": "application/json"})
        response = connection.getresponse()
        assert response.status == 403
        assert response.getheader("Access-Control-Allow-Origin") is None
        response.read()
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)
