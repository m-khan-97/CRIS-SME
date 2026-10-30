import importlib.util
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
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
    assert certificate.not_valid_after_utc > datetime.now(timezone.utc) + timedelta(days=364)


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
    trusted = []
    monkeypatch.setattr(pilot, "trust_browser", lambda state: trusted.append(state))
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
    assert trusted == [tmp_path]
    assert captured["command"] == ["/usr/bin/google-chrome", "--new-tab", pilot.CONSOLE]
    assert captured["env"].get("DISPLAY") == pilot.os.environ.get("DISPLAY")
    assert (tmp_path / "browser.log").stat().st_mode & 0o777 == 0o600


def aged_certificates(state, monkeypatch):
    class Earlier(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(tz) - timedelta(days=340)
    with monkeypatch.context() as patch:
        patch.setattr(pilot, "datetime", Earlier)
        pilot.certificates(state)


def test_renewal_retains_accounts_archives_private_material_and_is_idempotent(tmp_path, monkeypatch):
    aged_certificates(tmp_path, monkeypatch)
    (tmp_path / "accounts.json").write_text("unchanged identities")
    old = (tmp_path / "server.pem").read_bytes()
    pilot.renew_certificates(tmp_path)
    renewed = (tmp_path / "server.pem").read_bytes()
    assert renewed != old
    assert next((tmp_path / "certificate-history").glob("*/server.pem")).read_bytes() == old
    assert next((tmp_path / "certificate-history").glob("*/server-key.pem")).stat().st_mode & 0o777 == 0o600
    assert (tmp_path / "accounts.json").read_text() == "unchanged identities"
    pilot.renew_certificates(tmp_path)
    assert (tmp_path / "server.pem").read_bytes() == renewed
    assert not (tmp_path / "ca-key.pem").exists()


def test_renewal_requires_restart_and_rolls_back_on_trust_failure(tmp_path, monkeypatch):
    aged_certificates(tmp_path, monkeypatch)
    old = (tmp_path / "server.pem").read_bytes()
    (tmp_path / "api.pid.json").write_text(json.dumps({"pid": 123, "start": "same"}))
    monkeypatch.setattr(pilot, "process_identity", lambda pid: "same")
    with pytest.raises(ValueError, match="requires restart"):
        pilot.renew_certificates(tmp_path)
    assert (tmp_path / "server.pem").read_bytes() == old
    (tmp_path / "api.pid.json").unlink()
    (tmp_path / "browser-trust.json").write_text("{}")
    monkeypatch.setattr(pilot, "certificate_tool", lambda: "certutil")
    def fail(state):
        raise RuntimeError("trust failed")
    monkeypatch.setattr(pilot, "trust_browser", fail)
    with pytest.raises(RuntimeError, match="trust failed"):
        pilot.renew_certificates(tmp_path)
    assert (tmp_path / "server.pem").read_bytes() == old


def test_local_leaf_rejects_ca_and_mismatched_key(tmp_path):
    pilot.certificates(tmp_path)
    leaf = tmp_path / "server.pem"
    original = leaf.read_bytes()
    leaf.write_bytes((tmp_path / "ca.pem").read_bytes())
    with pytest.raises((ValueError, x509.ExtensionNotFound)):
        pilot.local_leaf(tmp_path)
    leaf.write_bytes(original)
    other = tmp_path / "other"
    other.mkdir()
    pilot.certificates(other)
    (tmp_path / "server-key.pem").write_bytes((other / "server-key.pem").read_bytes())
    with pytest.raises(ValueError, match="does not match"):
        pilot.local_leaf(tmp_path)


def test_real_nss_trust_is_exact_leaf_idempotent_and_removable(tmp_path, monkeypatch):
    import subprocess
    try:
        tool = pilot.certificate_tool()
    except ValueError:
        pytest.skip("Optional libnss3-tools not installed")
    state = tmp_path / "state"
    state.mkdir()
    database = tmp_path / "nssdb"
    monkeypatch.setattr(pilot, "browser_database", lambda: database)
    aged_certificates(state, monkeypatch)
    pilot.trust_browser(state)
    record = json.loads((state / "browser-trust.json").read_text())
    assert pilot.owned_trust(tool, record)
    assert "P,," in subprocess.check_output([tool, "-L", "-d", "sql:" + str(database)], text=True)
    assert "C,," not in subprocess.check_output([tool, "-L", "-d", "sql:" + str(database)], text=True)
    backups = list((state / "trust-backups").iterdir())
    pilot.trust_browser(state)
    assert json.loads((state / "browser-trust.json").read_text()) == record
    assert list((state / "trust-backups").iterdir()) == backups
    with pytest.raises(ValueError, match="not owned"):
        pilot.owned_trust(tool, {**record, "fingerprint": "0" * 64})
    pilot.renew_certificates(state)
    updated = json.loads((state / "browser-trust.json").read_text())
    assert updated["fingerprint"] != record["fingerprint"]
    assert pilot.owned_trust(tool, updated)
    assert record["nickname"] not in subprocess.check_output([tool, "-L", "-d", "sql:" + str(database)], text=True)
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in (state / "trust-backups").iterdir())
    # An unrelated certificate must survive removal of this pilot's trust.
    subprocess.run([tool, "-A", "-d", "sql:" + str(database), "-n", "unrelated", "-t", ",,",
                    "-i", str(state / "ca.pem")], check=True)
    pilot.trust_browser(state, remove=True)
    listing = subprocess.check_output([tool, "-L", "-d", "sql:" + str(database)], text=True)
    assert "CRIS localhost" not in listing and "unrelated" in listing
    assert not (state / "browser-trust.json").exists()


def test_browser_database_matches_chromium_legacy_precedence(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert pilot.browser_database() == tmp_path / ".local/share/pki/nssdb"
    legacy = tmp_path / ".pki/nssdb"
    legacy.mkdir(parents=True)
    assert pilot.browser_database() == legacy


def test_local_leaf_rejects_additional_non_local_names(tmp_path):
    from cryptography.hazmat.primitives import hashes, serialization
    pilot.certificates(tmp_path)
    original = pilot.local_leaf(tmp_path)
    key = serialization.load_pem_private_key((tmp_path / "server-key.pem").read_bytes(), password=None)
    certificate = (x509.CertificateBuilder().subject_name(original.subject).issuer_name(original.issuer)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(original.not_valid_before_utc).not_valid_after(original.not_valid_after_utc)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), True)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.DNSName("example.com")]), False)
        .sign(key, hashes.SHA256()))
    (tmp_path / "server.pem").write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    with pytest.raises(ValueError, match="exact localhost"):
        pilot.local_leaf(tmp_path)
