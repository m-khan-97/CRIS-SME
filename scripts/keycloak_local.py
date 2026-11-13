"""Private loopback Keycloak pilot. Never use this topology for public hosting."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import ipaddress
import json
import os
from pathlib import Path
import secrets
import signal
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

from cryptography import x509
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / ".local/keycloak"
ISSUER = "https://localhost:8443/realms/cris"
CONSOLE = "http://localhost:5174"
SERVICES = ("keycloak", "api", "worker", "console")


def write_private(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(value)
    path.chmod(0o600)


def realm_config(accounts):
    return {
        "realm": "cris", "displayName": "CRIS Local Identity", "enabled": True,
        "sslRequired": "all", "registrationAllowed": False, "resetPasswordAllowed": False,
        "bruteForceProtected": True, "defaultSignatureAlgorithm": "RS256", "accessTokenLifespan": 300,
        "defaultDefaultClientScopes": [], "defaultOptionalClientScopes": [],
        "clientScopes": [{"name": "cris.api", "protocol": "openid-connect",
            "attributes": {"include.in.token.scope": "true", "display.on.consent.screen": "false"},
            "protocolMappers": [{"name": "cris-api-audience", "protocol": "openid-connect",
                "protocolMapper": "oidc-audience-mapper", "consentRequired": False,
                "config": {"included.custom.audience": "cris-api", "access.token.claim": "true", "id.token.claim": "false"}},
                {"name": "cris-subject", "protocol": "openid-connect", "protocolMapper": "oidc-sub-mapper",
                 "consentRequired": False, "config": {"access.token.claim": "true", "introspection.token.claim": "true"}}]}],
        "clients": [{"clientId": "cris-console", "name": "CRIS Enterprise Console", "protocol": "openid-connect",
            "enabled": True, "publicClient": True, "standardFlowEnabled": True,
            "directAccessGrantsEnabled": False, "implicitFlowEnabled": False, "serviceAccountsEnabled": False,
            "fullScopeAllowed": False, "redirectUris": [f"{CONSOLE}/auth/callback"], "webOrigins": [CONSOLE],
            "defaultClientScopes": [], "optionalClientScopes": ["cris.api"],
            "attributes": {"pkce.code.challenge.method": "S256"}}],
        "users": [{"id": row["id"], "username": row["username"], "enabled": True,
            "email": row["username"] + "@example.invalid", "emailVerified": True,
            "firstName": "CRIS", "lastName": row["label"], "requiredActions": [],
            "credentials": [{"type": "password", "value": row["password"], "temporary": False}]}
            for row in accounts.values() if row.get("id")],
    }


def certificates(state):
    now = datetime.now(timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "CRIS local development CA")])
    ca = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(ca_key.public_key())
          .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=5))
          .not_valid_after(now + timedelta(days=3650)).add_extension(x509.BasicConstraints(ca=True, path_length=0), True)
          .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), True)
          .sign(ca_key, hashes.SHA256()))
    # NSS groups certificates by subject; a generation ID prevents renewal aliases
    # from resolving an older nickname to the newly imported certificate.
    server = (x509.CertificateBuilder().subject_name(x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, str(uuid4()))]))
        .issuer_name(name).public_key(server_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), True)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), False)
        .add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]), False)
        .sign(ca_key, hashes.SHA256()))
    for filename, content in (("ca.pem", ca.public_bytes(serialization.Encoding.PEM)),
        ("server.pem", server.public_bytes(serialization.Encoding.PEM) + ca.public_bytes(serialization.Encoding.PEM)),
        ("server-key.pem", server_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))):
        write_private(state / filename, content.decode())
    # The issuing private key is deliberately not retained by this local pilot.
    import base64
    digest = hashes.Hash(hashes.SHA256())
    digest.update(server_key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo))
    write_private(state / "certificate-spki.txt", base64.b64encode(digest.finalize()).decode() + "\n")


def certificate_tool():
    executable = shutil.which("certutil")
    bundled = ROOT / ".venv/nss-tools/usr/bin/certutil"
    if not executable and bundled.is_file():
        executable = str(bundled)
    if not executable:
        raise ValueError("Install libnss3-tools to enable normal Chrome/Chromium certificate trust.")
    return executable


def browser_database():
    legacy = Path.home() / ".pki/nssdb"
    return legacy if legacy.exists() else Path.home() / ".local/share/pki/nssdb"


def local_leaf(state):
    leaf = x509.load_pem_x509_certificate((state / "server.pem").read_bytes())
    names = leaf.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    allowed = {x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))}
    now = datetime.now(timezone.utc)
    if (leaf.extensions.get_extension_for_class(x509.BasicConstraints).value.ca
            or set(names) != allowed or not leaf.not_valid_before_utc <= now < leaf.not_valid_after_utc):
        raise ValueError("Browser trust requires a valid, non-CA, exact localhost/127.0.0.1 certificate.")
    key = serialization.load_pem_private_key((state / "server-key.pem").read_bytes(), password=None)
    if leaf.public_key().public_numbers() != key.public_key().public_numbers():
        raise ValueError("Local certificate does not match the pilot private key.")
    return leaf


def owned_trust(tool, record):
    result = subprocess.run([tool, "-L", "-d", "sql:" + record["database"], "-n", record["nickname"], "-a"],
                            capture_output=True, text=True)
    if result.returncode:
        return False
    leaf = x509.load_pem_x509_certificate(result.stdout.encode())
    if leaf.fingerprint(hashes.SHA256()).hex() != record["fingerprint"]:
        raise ValueError("Refusing to change a browser certificate not owned by this pilot.")
    return True


def trust_browser(state, *, remove=False):
    tool = certificate_tool()
    record_path = state / "browser-trust.json"
    previous = json.loads(record_path.read_text()) if record_path.exists() else None
    if remove:
        if previous and owned_trust(tool, previous):
            subprocess.run([tool, "-D", "-d", "sql:" + previous["database"], "-n", previous["nickname"]], check=True)
        record_path.unlink(missing_ok=True)
        print("Removed only this pilot's recorded browser certificate trust.")
        return
    leaf = local_leaf(state)
    fingerprint = leaf.fingerprint(hashes.SHA256()).hex()
    database = browser_database()
    database.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not (database / "cert9.db").exists():
        subprocess.run([tool, "-N", "-d", "sql:" + str(database), "--empty-password"], check=True)
    record = {"database": str(database), "nickname": "CRIS localhost " + fingerprint, "fingerprint": fingerprint}
    if previous:
        owned_trust(tool, previous)
    if previous == record:
        listing = subprocess.run([tool, "-L", "-d", "sql:" + str(database)],
                                 capture_output=True, text=True, check=True).stdout
        if any(line.startswith(record["nickname"]) and line.split()[-1] == "P,," for line in listing.splitlines()):
            return
    # Back up the public certificate database consistently, never the user's private-key database.
    backup = state / "trust-backups" / (str(uuid4()) + ".db")
    backup.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with sqlite3.connect(str(database / "cert9.db")) as source, sqlite3.connect(str(backup)) as target:
        source.backup(target)
    backup.chmod(0o600)
    with tempfile.TemporaryDirectory(dir=state) as directory:
        pem = Path(directory) / "leaf.pem"
        write_private(pem, leaf.public_bytes(serialization.Encoding.PEM).decode())
        # P trusts only this exact TLS peer, not its CA or arbitrary issued certificates.
        subprocess.run([tool, "-A", "-d", "sql:" + str(database), "-n", record["nickname"],
                        "-t", "P,,", "-i", str(pem)], check=True)
    temporary = state / ("browser-trust-" + str(uuid4()) + ".json")
    write_private(temporary, json.dumps(record, indent=2) + "\n")
    temporary.replace(record_path)
    if previous and previous != record:
        try:
            if owned_trust(tool, previous):
                subprocess.run([tool, "-D", "-d", "sql:" + previous["database"], "-n", previous["nickname"]], check=True)
        except (ValueError, subprocess.CalledProcessError):
            # New trust is committed; a cleanup error must not roll back the active certificate.
            print("Warning: old browser certificate cleanup failed; unrelated entries were left untouched.", file=sys.stderr)
    print("Exact localhost TLS peer trusted for normal Chrome/Chromium. No CA or system-wide trust added.")


def renew_certificates(state):
    leaf = x509.load_pem_x509_certificate((state / "server.pem").read_bytes())
    if leaf.not_valid_after_utc > datetime.now(timezone.utc) + timedelta(days=30):
        return
    for service in SERVICES:
        path = state / f"{service}.pid.json"
        saved = json.loads(path.read_text()) if path.exists() else {}
        if saved.get("start") and process_identity(saved["pid"]) == saved["start"]:
            raise ValueError("Certificate renewal requires restart; running services have not been changed.")
    if (state / "browser-trust.json").exists():
        certificate_tool()
    archive = state / "certificate-history" / str(uuid4())
    archive.mkdir(parents=True, mode=0o700)
    filenames = ("ca.pem", "server.pem", "server-key.pem", "certificate-spki.txt")
    with tempfile.TemporaryDirectory(dir=state) as directory:
        replacement = Path(directory)
        certificates(replacement)
        for name in filenames:
            shutil.copy2(state / name, archive / name)
        try:
            for name in filenames:
                (replacement / name).replace(state / name)
            if (state / "browser-trust.json").exists():
                trust_browser(state)
        except Exception:
            for name in filenames:
                shutil.copy2(archive / name, state / name)
            raise
    print("Renewed localhost certificate; identities and assessment data retained.")


def prepare(state, args):
    if (state / "settings.json").exists():
        raise ValueError("Existing pilot state found; use start/status. Preparation never overwrites identities or secrets.")
    keycloak = args.keycloak_home.resolve()
    java = args.java_home.resolve()
    pg = args.pg_bin.resolve()
    for required in (keycloak / "bin/kc.sh", java / "bin/java", pg / "initdb"):
        if not required.is_file():
            raise ValueError(f"Required executable missing: {required}")
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    state.chmod(0o700)
    accounts = {label: {"id": str(uuid4()), "label": label, "username": "cris-" + label,
                       "password": secrets.token_urlsafe(24)} for label in ("owner", "analyst", "outsider")}
    accounts["admin"] = {"username": "cris-local-admin", "password": secrets.token_urlsafe(24)}
    certificates(state)
    settings = {"keycloak_home": str(keycloak), "java_home": str(java), "pg_bin": str(pg),
        "pg_password": secrets.token_hex(24), "encryption_key": Fernet.generate_key().decode()}
    write_private(state / "accounts.json", json.dumps(accounts, indent=2) + "\n")
    write_private(state / "settings.json", json.dumps(settings, indent=2) + "\n")
    write_private(state / "postgres-password", settings["pg_password"])
    import_dir = keycloak / "data/import"
    import_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    write_private(import_dir / "cris-realm.json", json.dumps(realm_config(accounts), indent=2) + "\n")
    login = accounts["owner"]
    admin = accounts["admin"]
    write_private(state / "login.txt", f"LOCAL DEVELOPMENT ONLY\nConsole: {CONSOLE}\nUsername: {login['username']}\nPassword: {login['password']}\n\nKeycloak: https://localhost:8443/admin/\nAdmin username: {admin['username']}\nAdmin password: {admin['password']}\n\nRun keycloak_local.py trust-browser for exact localhost peer trust in Chrome/Chromium. Credentials and certificates are not production assets.\n")
    print(f"Private pilot prepared. Credentials: {state / 'login.txt'}")


def environment(state):
    settings = json.loads((state / "settings.json").read_text())
    env = dict(os.environ)
    # Cloud credentials are deliberately not provisioned or copied into pilot files.
    env.update({"PYTHONPATH": str(ROOT / "src"), "JAVA_HOME": settings["java_home"],
        "JAVA_OPTS_KC_HEAP": "-Xms64m -Xmx512m",
        "LD_LIBRARY_PATH": str(ROOT / ".venv/pg-root/usr/lib/x86_64-linux-gnu"),
        "CRIS_ENTERPRISE_DATABASE_URL": f"postgresql+psycopg://cris:{settings['pg_password']}@127.0.0.1:55433/cris",
        "CRIS_ENTERPRISE_ENCRYPTION_KEY": settings["encryption_key"],
        "CRIS_ENTERPRISE_OIDC_ISSUER": ISSUER, "CRIS_ENTERPRISE_OIDC_AUDIENCE": "cris-api",
        "CRIS_ENTERPRISE_JWKS_URL": ISSUER + "/protocol/openid-connect/certs",
        "CRIS_ENTERPRISE_OIDC_CLIENT_ID": "cris-console",
        "CRIS_ENTERPRISE_AUTHORIZE_URL": ISSUER + "/protocol/openid-connect/auth",
        "CRIS_ENTERPRISE_TOKEN_URL": ISSUER + "/protocol/openid-connect/token",
        "CRIS_ENTERPRISE_OIDC_CA_FILE": str(state / "ca.pem"),
        "CRIS_ENTERPRISE_ARTIFACT_ROOT": str(state / "artifacts"),
        "CRIS_ENTERPRISE_STORAGE_BACKEND": "local",
        "CRIS_ENTERPRISE_DATABASE_PROFILE": "development",
        "CRIS_ENTERPRISE_RETENTION_ENABLED": "false",
        "CRIS_ENTERPRISE_ALLOWED_HOSTS": "localhost,127.0.0.1",
        "VITE_OIDC_AUTHORITY": ISSUER, "VITE_OIDC_CLIENT_ID": "cris-console", "VITE_OIDC_SCOPE": "openid cris.api"})
    env.pop("VITE_API_BASE_URL", None)
    env.pop("VITE_DEMO_MODE", None)
    return env


def pg_command(state, command):
    settings = json.loads((state / "settings.json").read_text())
    return [str(Path(settings["pg_bin"]) / command)]


def postgres(state):
    env = environment(state)
    cluster = state / "postgres"
    socket = state / "socket"
    socket.mkdir(exist_ok=True, mode=0o700)
    with (state / "postgres-setup.log").open("a") as log:
        if not (cluster / "PG_VERSION").exists():
            subprocess.run(pg_command(state, "initdb") + ["-D", str(cluster), "-U", "cris", "--auth-local=trust",
                "--auth-host=scram-sha-256", "--pwfile", str(state / "postgres-password")], env=env, stdout=log, stderr=log, check=True)
        status = subprocess.run(pg_command(state, "pg_ctl") + ["-D", str(cluster), "status"], env=env, stdout=log, stderr=log)
        if status.returncode:
            subprocess.run(pg_command(state, "pg_ctl") + ["-D", str(cluster), "-l", str(state / "postgres.log"), "-o",
                f"-h 127.0.0.1 -p 55433 -k {socket}", "start"], env=env, stdout=log, stderr=log, check=True)
        # Query before create so a restart never drops or resets an existing database.
        result = subprocess.run(pg_command(state, "psql") + ["-h", str(socket), "-p", "55433", "-U", "cris", "-d", "postgres",
            "-Atc", "SELECT 1 FROM pg_database WHERE datname='cris'"], env=env, capture_output=True, text=True, check=True)
        if not result.stdout.strip():
            subprocess.run(pg_command(state, "createdb") + ["-h", str(socket), "-p", "55433", "-U", "cris", "cris"], env=env, stdout=log, stderr=log, check=True)


def process_identity(pid):
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return fields[19] if fields[0] not in {"Z", "X"} else None
    except (FileNotFoundError, ProcessLookupError):
        return None


def start_service(state, service):
    record = state / f"{service}.pid.json"
    if record.exists():
        saved = json.loads(record.read_text())
        if saved["start"] and process_identity(saved["pid"]) == saved["start"]:
            return
    with (state / f"{service}.log").open("a") as log:
        child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "serve", service, "--state-dir", str(state)],
            env=environment(state), cwd=ROOT, stdout=log, stderr=log, start_new_session=True)
    identity = process_identity(child.pid)
    record.write_text(json.dumps({"pid": child.pid, "start": identity}))


def serve(state, service):
    settings = json.loads((state / "settings.json").read_text())
    env = environment(state)
    if service == "keycloak":
        admin = json.loads((state / "accounts.json").read_text())["admin"]
        env.update({"KC_BOOTSTRAP_ADMIN_USERNAME": admin["username"], "KC_BOOTSTRAP_ADMIN_PASSWORD": admin["password"]})
        command = [str(Path(settings["keycloak_home"]) / "bin/kc.sh"), "start", "--db=dev-file", "--cache=local", "--http-enabled=false", "--http-host=127.0.0.1",
            "--https-port=8443", "--hostname=https://localhost:8443", "--https-certificate-file=" + str(state / "server.pem"),
            "--https-certificate-key-file=" + str(state / "server-key.pem"), "--import-realm"]
    elif service in {"api", "worker"}:
        command = [sys.executable, "-m", "cris_sme.enterprise", "serve" if service == "api" else "worker"]
    else:
        os.chdir(ROOT / "frontend/console")
        command = ["npm", "run", "dev:enterprise", "--", "--host", "127.0.0.1", "--port", "5174", "--strictPort"]
    os.execvpe(command[0], command, env)


def wait_ready(state, url, *, tls=False):
    import ssl
    import httpx
    context = ssl.create_default_context(cafile=str(state / "ca.pem")) if tls else True
    with httpx.Client(verify=context, timeout=2, trust_env=False, follow_redirects=False) as client:
        for _ in range(90):
            try:
                response = client.get(url)
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(1)
    raise RuntimeError(f"Service did not become ready: {url}. Check private pilot logs.")


def sync_realm(state):
    """Add missing CRIS mappers without replacing the realm, users or sessions."""
    import ssl
    import httpx
    accounts = json.loads((state / "accounts.json").read_text())
    admin = accounts["admin"]
    context = ssl.create_default_context(cafile=str(state / "ca.pem"))
    with httpx.Client(verify=context, trust_env=False, follow_redirects=False, timeout=15) as client:
        response = client.post("https://localhost:8443/realms/master/protocol/openid-connect/token", data={
            "grant_type": "password", "client_id": "admin-cli", "username": admin["username"], "password": admin["password"]})
        response.raise_for_status()
        client.headers["Authorization"] = "Bearer " + response.json()["access_token"]
        base = "https://localhost:8443/admin/realms/cris/client-scopes"
        response = client.get(base)
        response.raise_for_status()
        scopes = [row for row in response.json() if row["name"] == "cris.api"]
        if len(scopes) != 1:
            raise ValueError("Expected exactly one local CRIS API scope")
        scope = scopes[0]
        existing = {mapper["name"] for mapper in scope.get("protocolMappers", [])}
        for mapper in realm_config(accounts)["clientScopes"][0]["protocolMappers"]:
            if mapper["name"] not in existing:
                response = client.post(f"{base}/{scope['id']}/protocol-mappers/models", json=mapper)
                response.raise_for_status()
    print("Local CRIS realm mapper configuration checked; users and memberships retained.")


def start(state):
    renew_certificates(state)
    postgres(state)
    env = environment(state)
    subprocess.run([sys.executable, "-m", "cris_sme.enterprise", "migrate"], env=env, check=True)
    from cris_sme.enterprise.auth import Principal
    from cris_sme.enterprise.store import Store
    store = Store.connect(env["CRIS_ENTERPRISE_DATABASE_URL"], env["CRIS_ENTERPRISE_ENCRYPTION_KEY"])
    accounts = json.loads((state / "accounts.json").read_text())
    owner = Principal(ISSUER, accounts["owner"]["id"])
    if not store.tenants(owner):
        tenant = store.bootstrap(owner, "CRIS Local Workspace")
        store.member(tenant, owner, accounts["analyst"]["id"], "analyst")
    outsider = Principal(ISSUER, accounts["outsider"]["id"])
    if not store.tenants(outsider):
        store.bootstrap(outsider, "CRIS Isolation Workspace")
    store.engine.dispose()
    start_service(state, "keycloak")
    wait_ready(state, ISSUER + "/.well-known/openid-configuration", tls=True)
    start_service(state, "api")
    wait_ready(state, "http://127.0.0.1:8788/ready")
    start_service(state, "worker")
    start_service(state, "console")
    wait_ready(state, CONSOLE)
    print(f"Local identity pilot ready: {CONSOLE}. Private credentials: {state / 'login.txt'}")


def stop(state):
    for service in reversed(SERVICES):
        record = state / f"{service}.pid.json"
        if not record.exists():
            continue
        saved = json.loads(record.read_text())
        if saved["start"] and process_identity(saved["pid"]) == saved["start"]:
            try:
                os.killpg(saved["pid"], signal.SIGTERM)
                deadline = time.monotonic() + 30
                while process_identity(saved["pid"]) == saved["start"] and time.monotonic() < deadline:
                    time.sleep(0.1)
                if process_identity(saved["pid"]) == saved["start"]:
                    os.killpg(saved["pid"], signal.SIGKILL)
            except ProcessLookupError:
                pass
        record.unlink()
    subprocess.run(pg_command(state, "pg_ctl") + ["-D", str(state / "postgres"), "stop", "-m", "fast"], env=environment(state), check=False)
    print("Local pilot services stopped; private identity/database state retained.")


def browser_environment():
    env = dict(os.environ)
    # IDE sandbox GTK overrides can crash the host browser before a window opens.
    for key in ("GSETTINGS_SCHEMA_DIR", "GTK_PATH", "GTK_EXE_PREFIX", "GTK_DATA_PREFIX",
                "GDK_PIXBUF_MODULE_FILE", "GIO_EXTRA_MODULES", "QT_PLUGIN_PATH",
                "QT_QPA_PLATFORM_PLUGIN_PATH", "LD_LIBRARY_PATH"):
        env.pop(key, None)
    directories = env.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":")
    env["XDG_DATA_DIRS"] = ":".join(directory for directory in directories if directory and not any(
        left == "snap" and right == "code" for left, right in zip(Path(directory).parts, Path(directory).parts[1:])
    )) or "/usr/local/share:/usr/share"
    return env


def browser(state):
    executable = shutil.which("google-chrome") or shutil.which("chromium")
    if not executable:
        raise ValueError("Install Chrome/Chromium to open the local pilot.")
    trust_browser(state)
    log_path = state / "browser.log"
    with log_path.open("a") as log:
        child = subprocess.Popen([executable, "--new-tab", CONSOLE],
            start_new_session=True, env=browser_environment(), stdout=log, stderr=log)
    log_path.chmod(0o600)
    try:
        code = child.wait(timeout=2)
    except subprocess.TimeoutExpired:
        print("Opened the console in your normal browser profile.")
    else:
        if code:
            raise RuntimeError(f"Local browser failed to start (exit {code}). Check {log_path}")
        print("Sent the console URL to your normal browser profile.")


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "start", "stop", "restart", "serve", "status", "browser", "trust-browser", "untrust-browser", "sync-realm"])
    parser.add_argument("service", nargs="?", choices=SERVICES)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--keycloak-home", type=Path)
    parser.add_argument("--java-home", type=Path)
    parser.add_argument("--pg-bin", type=Path)
    args = parser.parse_args()
    state = args.state_dir.resolve()
    if args.command == "prepare":
        if not all((args.keycloak_home, args.java_home, args.pg_bin)):
            parser.error("prepare requires --keycloak-home, --java-home and --pg-bin")
        prepare(state, args)
    elif args.command == "start":
        start(state)
    elif args.command == "stop":
        stop(state)
    elif args.command == "restart":
        stop(state)
        start(state)
    elif args.command == "browser":
        browser(state)
    elif args.command in {"trust-browser", "untrust-browser"}:
        trust_browser(state, remove=args.command == "untrust-browser")
    elif args.command == "sync-realm":
        sync_realm(state)
    elif args.command == "status":
        for service in SERVICES:
            record = state / f"{service}.pid.json"
            saved = json.loads(record.read_text()) if record.exists() else {}
            running = bool(saved.get("start")) and process_identity(saved.get("pid")) == saved.get("start")
            print(f"{service}: {'running' if running else 'stopped'}")
    elif args.service:
        serve(state, args.service)
    else:
        parser.error("serve requires a service")


if __name__ == "__main__":
    main()
