import importlib.util
import json
from pathlib import Path
import ssl
from types import SimpleNamespace

from cryptography import x509
import pytest

from cris_sme.enterprise.auth import AccessTokenVerifier

spec = importlib.util.spec_from_file_location("keycloak_local", Path(__file__).resolve().parents[2] / "scripts/keycloak_local.py")
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


def test_realm_has_exact_origin_pkce_and_no_password_grant():
    realm = pilot.realm_config({"owner": {"id": "owner", "username": "owner", "label": "owner", "password": "test-only-password"}})
    client = realm["clients"][0]
    assert client["publicClient"] and client["standardFlowEnabled"]
    assert client["attributes"]["pkce.code.challenge.method"] == "S256"
    assert client["redirectUris"] == ["http://localhost:5174/auth/callback"]
    assert client["webOrigins"] == ["http://localhost:5174"]
    assert not any(client[key] for key in ("directAccessGrantsEnabled", "implicitFlowEnabled", "serviceAccountsEnabled", "fullScopeAllowed"))
    assert realm["sslRequired"] == "all" and realm["accessTokenLifespan"] <= 3600
    mapper = realm["clientScopes"][0]["protocolMappers"][0]["config"]
    assert mapper["included.custom.audience"] == "cris-api" and mapper["id.token.claim"] == "false"
    assert any(row["protocolMapper"] == "oidc-sub-mapper" and row["config"]["access.token.claim"] == "true"
               for row in realm["clientScopes"][0]["protocolMappers"])


def test_private_certificates_and_ca_verification(tmp_path):
    pilot.certificates(tmp_path)
    certificate = x509.load_pem_x509_certificate((tmp_path / "server.pem").read_bytes())
    assert "localhost" in certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName)
    verifier = AccessTokenVerifier("https://localhost:8443/realms/cris", "cris-api", "https://localhost:8443/keys", ca_file=str(tmp_path / "ca.pem"))
    assert verifier._tls.verify_mode == ssl.CERT_REQUIRED
    assert verifier._tls.check_hostname is True
    for path in tmp_path.iterdir():
        assert path.stat().st_mode & 0o777 == 0o600
    assert not (tmp_path / "ca-key.pem").exists()


def test_missing_ca_fails_at_configuration(tmp_path):
    with pytest.raises(OSError):
        AccessTokenVerifier("https://localhost", "api", "https://localhost/keys", ca_file=str(tmp_path / "missing.pem"))


def test_prepare_checks_executables_before_creating_secrets(tmp_path):
    state = tmp_path / "state"
    args = SimpleNamespace(keycloak_home=tmp_path, java_home=tmp_path, pg_bin=tmp_path)
    with pytest.raises(ValueError, match="Required executable"):
        pilot.prepare(state, args)
    assert not state.exists()


def test_prepare_never_overwrites_existing_state(tmp_path):
    (tmp_path / "settings.json").write_text("existing-state")
    with pytest.raises(ValueError, match="never overwrites"):
        pilot.prepare(tmp_path, None)
    assert (tmp_path / "settings.json").read_text() == "existing-state"


def test_environment_keeps_private_credentials_out_of_vite(tmp_path, monkeypatch):
    monkeypatch.setenv("CRIS_ENTERPRISE_STORAGE_BACKEND", "s3")
    monkeypatch.setenv("CRIS_ENTERPRISE_RETENTION_ENABLED", "true")
    (tmp_path / "settings.json").write_text(json.dumps({"java_home": "java", "pg_password": "test-private-password", "encryption_key": "test-private-key"}))
    env = pilot.environment(tmp_path)
    public = {key: value for key, value in env.items() if key.startswith("VITE_")}
    assert "test-private" not in json.dumps(public)
    assert env["CRIS_ENTERPRISE_OIDC_CA_FILE"] == str(tmp_path / "ca.pem")
    assert env["CRIS_ENTERPRISE_OIDC_AUDIENCE"] == "cris-api"
    assert env["CRIS_ENTERPRISE_STORAGE_BACKEND"] == "local"
    assert env["CRIS_ENTERPRISE_RETENTION_ENABLED"] == "false"


def test_process_identity_ignores_dead_and_reused_processes(monkeypatch):
    monkeypatch.setattr(Path, "read_text", lambda self: "123 (name with spaces) " + " ".join(["S", *(["0"] * 18), "12345"]))
    assert pilot.process_identity(123) == "12345"
    monkeypatch.setattr(Path, "read_text", lambda self: "123 (name) " + " ".join(["Z", *(["0"] * 18), "12345"]))
    assert pilot.process_identity(123) is None
    def missing(self):
        raise ProcessLookupError()
    monkeypatch.setattr(Path, "read_text", missing)
    assert pilot.process_identity(123) is None


def test_stop_never_signals_a_reused_pid(tmp_path, monkeypatch):
    (tmp_path / "api.pid.json").write_text(json.dumps({"pid": 123, "start": "old-start"}))
    monkeypatch.setattr(pilot, "process_identity", lambda pid: "new-start")
    killed = []
    monkeypatch.setattr(pilot.os, "killpg", lambda *args: killed.append(args))
    monkeypatch.setattr(pilot, "pg_command", lambda *args: ["pg_ctl"])
    monkeypatch.setattr(pilot, "environment", lambda state: {})
    monkeypatch.setattr(pilot.subprocess, "run", lambda *args, **kwargs: None)
    pilot.stop(tmp_path)
    assert killed == []


def test_browser_environment_removes_ide_overrides_without_changing_host(monkeypatch):
    monkeypatch.setenv("GSETTINGS_SCHEMA_DIR", "/snap/code/schemas")
    monkeypatch.setenv("GTK_PATH", "/snap/code/gtk")
    monkeypatch.setenv("XDG_DATA_DIRS", "/home/example/snap/code/272:/snap/code/272/usr/share:/usr/share/gnome:/usr/share")
    monkeypatch.setenv("DISPLAY", ":0")
    env = pilot.browser_environment()
    assert "GSETTINGS_SCHEMA_DIR" not in env and "GTK_PATH" not in env
    assert env["XDG_DATA_DIRS"] == "/usr/share/gnome:/usr/share"
    assert env["DISPLAY"] == ":0"
    assert pilot.os.environ["GTK_PATH"] == "/snap/code/gtk"


@pytest.mark.parametrize("exit_code", [0, 133, None])
def test_browser_launch_checks_exit_status_and_keeps_errors_private(tmp_path, monkeypatch, capsys, exit_code):
    import subprocess
    (tmp_path / "certificate-spki.txt").write_text("public-key-pin\n")
    monkeypatch.setattr(pilot.shutil, "which", lambda name: "/usr/bin/google-chrome")
    captured = {}
    def launch(command, **kwargs):
        captured.update(command=command, **kwargs)
        def wait(timeout):
            if exit_code is None:
                raise subprocess.TimeoutExpired(command, timeout)
            return exit_code
        return SimpleNamespace(wait=wait)
    monkeypatch.setattr(pilot.subprocess, "Popen", launch)
    if exit_code:
        with pytest.raises(RuntimeError, match="failed to start"):
            pilot.browser(tmp_path)
        assert "Opened" not in capsys.readouterr().out
    else:
        pilot.browser(tmp_path)
        assert "browser profile" in capsys.readouterr().out
    assert "--ignore-certificate-errors-spki-list=public-key-pin" in captured["command"]
    assert "--ignore-certificate-errors" not in captured["command"]
    assert captured["env"].get("DISPLAY") == pilot.os.environ.get("DISPLAY")
    assert (tmp_path / "browser.log").stat().st_mode & 0o777 == 0o600
