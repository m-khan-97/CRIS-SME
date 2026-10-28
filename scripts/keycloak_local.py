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
import subprocess
import sys
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
          .not_valid_after(now + timedelta(days=30)).add_extension(x509.BasicConstraints(ca=True, path_length=0), True)
          .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), True)
          .sign(ca_key, hashes.SHA256()))
    server = (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")]))
        .issuer_name(name).public_key(server_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=30))
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
    write_private(state / "login.txt", f"LOCAL DEVELOPMENT ONLY\nConsole: {CONSOLE}\nUsername: {login['username']}\nPassword: {login['password']}\n\nKeycloak: https://localhost:8443/admin/\nAdmin username: {admin['username']}\nAdmin password: {admin['password']}\n\nTrust only this pilot's ca.pem for localhost. Credentials and certificates are not production assets.\n")
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


def browser(state):
    executable = shutil.which("google-chrome") or shutil.which("chromium")
    if not executable:
        raise ValueError("Install Chrome/Chromium or trust this pilot's ca.pem in your browser manually.")
    pin = (state / "certificate-spki.txt").read_text().strip()
    subprocess.Popen([executable, "--user-data-dir=" + str(state / "browser-profile"),
        "--ignore-certificate-errors-spki-list=" + pin, CONSOLE], start_new_session=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("Opened a separate local-pilot browser profile, pinned to this server's TLS public key.")


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "start", "stop", "restart", "serve", "status", "browser", "sync-realm"])
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
