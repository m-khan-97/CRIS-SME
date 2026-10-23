import sys

from cris_sme.enterprise import __main__ as cli
from cris_sme.enterprise.auth import Principal
from tests.enterprise.conftest import ISSUER
import pytest


@pytest.mark.parametrize("command", ["migrate", "bootstrap", "worker", "serve"])
def test_operator_commands_use_explicit_configuration(store, tmp_path, monkeypatch, capsys, command):
    variables = {"DATABASE_URL": "postgresql+psycopg://fixture", "ENCRYPTION_KEY": "fixture",
                 "OIDC_ISSUER": ISSUER, "OIDC_AUDIENCE": "cris-api", "JWKS_URL": ISSUER + "/keys",
                 "OIDC_CLIENT_ID": "browser", "AUTHORIZE_URL": ISSUER + "/authorize",
                 "TOKEN_URL": ISSUER + "/token", "ARTIFACT_ROOT": str(tmp_path)}
    for key, value in variables.items():
        monkeypatch.setenv("CRIS_ENTERPRISE_" + key, value)
    monkeypatch.setattr(cli.Store, "connect", lambda *args: store)
    monkeypatch.setattr(cli.os, "umask", lambda mask: None)
    calls = []
    monkeypatch.setattr(cli, "run_worker", lambda *args: calls.append(args))
    import uvicorn
    monkeypatch.setattr(uvicorn, "run", lambda app, **kwargs: calls.append(kwargs))
    args = ["enterprise", command]
    if command == "bootstrap":
        args.extend(["--name", "New organization", "--subject", "new-owner"])
    monkeypatch.setattr(sys, "argv", args)
    cli.main()
    if command == "bootstrap":
        assert store.tenants(Principal(ISSUER, "new-owner"))[0]["id"] == capsys.readouterr().out.strip()
    elif command == "serve":
        assert calls[0]["limit_concurrency"] == 32 and calls[0]["access_log"] is False
    elif command == "worker":
        assert calls[0][1] == tmp_path
