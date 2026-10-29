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


def test_historical_cli_defaults_to_preview_then_applies_explicitly(context, tmp_path, monkeypatch, capsys):
    import json
    from tests.enterprise.test_historical import source
    ctx = context
    root, name, _ = source(tmp_path)
    monkeypatch.setenv("CRIS_ENTERPRISE_DATABASE_URL", "postgresql+psycopg://fixture")
    monkeypatch.setenv("CRIS_ENTERPRISE_ENCRYPTION_KEY", "fixture")
    monkeypatch.setenv("CRIS_ENTERPRISE_OIDC_ISSUER", ISSUER)
    monkeypatch.setenv("CRIS_ENTERPRISE_ARTIFACT_ROOT", str(ctx["root"]))
    monkeypatch.setattr(cli.Store, "connect", lambda *args: ctx["store"])
    monkeypatch.setattr(cli.os, "umask", lambda mask: None)
    args = ["enterprise", "historical-import", "--tenant", ctx["tenant"], "--subject", "owner",
            "--source-root", str(root), "--report", str(name)]
    monkeypatch.setattr(sys, "argv", args)
    cli.main()
    assert json.loads(capsys.readouterr().out)["dry_run"] is True
    assert ctx["store"].job_list(ctx["tenant"], ctx["principal"]) == []
    monkeypatch.setattr(sys, "argv", args + ["--apply"])
    cli.main()
    created = json.loads(capsys.readouterr().out)
    assert created["created"] is True
    cli.main()
    assert json.loads(capsys.readouterr().out) == {**created, "created": False}


def test_recovery_cli_requires_explicit_restore_and_checks_bundle(store, tmp_path, monkeypatch, capsys):
    import json
    from tests.enterprise.test_recovery import isolated
    root = tmp_path / "artifacts"
    root.mkdir()
    monkeypatch.setenv("CRIS_ENTERPRISE_DATABASE_URL", "postgresql+psycopg://fixture")
    monkeypatch.setenv("CRIS_ENTERPRISE_ENCRYPTION_KEY", "fixture")
    monkeypatch.setenv("CRIS_ENTERPRISE_ARTIFACT_ROOT", str(root))
    monkeypatch.setattr(cli.Store, "connect", lambda *args: store)
    monkeypatch.setattr(cli.os, "umask", lambda mask: None)
    destination = tmp_path / "backup"
    for command in ["backup", "check-backup"]:
        monkeypatch.setattr(sys, "argv", ["enterprise", command, "--backup-dir", str(destination)])
        cli.main()
        assert json.loads(capsys.readouterr().out)["artifacts"] == 0
    with isolated(store) as target:
        monkeypatch.setattr(cli.Store, "connect", lambda *args: target)
        monkeypatch.setenv("CRIS_ENTERPRISE_ARTIFACT_ROOT", str(tmp_path / "restored"))
        args = ["enterprise", "restore", "--backup-dir", str(destination)]
        monkeypatch.setattr(sys, "argv", args)
        with pytest.raises(SystemExit):
            cli.main()
        monkeypatch.setattr(sys, "argv", args + ["--apply"])
        cli.main()
        assert json.loads(capsys.readouterr().out)["connections_disabled"] is True


@pytest.mark.parametrize("command", ["backup", "check-backup", "restore"])
def test_recovery_cli_requires_directory(store, monkeypatch, command):
    monkeypatch.setenv("CRIS_ENTERPRISE_DATABASE_URL", "postgresql+psycopg://fixture")
    monkeypatch.setenv("CRIS_ENTERPRISE_ENCRYPTION_KEY", "fixture")
    monkeypatch.setattr(cli.Store, "connect", lambda *args: store)
    monkeypatch.setattr(sys, "argv", ["enterprise", command])
    with pytest.raises(SystemExit):
        cli.main()
