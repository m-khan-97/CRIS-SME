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


def test_database_commands_preview_apply_and_check_roles(store, monkeypatch, capsys):
    import json
    monkeypatch.setenv("CRIS_ENTERPRISE_DATABASE_URL", "postgresql+psycopg://fixture")
    monkeypatch.setenv("CRIS_ENTERPRISE_ENCRYPTION_KEY", "fixture")
    monkeypatch.setattr(cli.Store, "connect", lambda *args: store)
    calls = []
    monkeypatch.setattr(cli.database_security, "harden", lambda engine, api, worker, **kw: calls.append((api, worker, kw)) or kw)
    monkeypatch.setattr(sys, "argv", ["enterprise", "database-harden", "--api-role", "cris_api", "--worker-role", "cris_worker"])
    cli.main()
    assert json.loads(capsys.readouterr().out) == {"apply": False}
    monkeypatch.setattr(sys, "argv", sys.argv + ["--apply"])
    cli.main()
    assert json.loads(capsys.readouterr().out) == {"apply": True}
    assert calls == [("cris_api", "cris_worker", {"apply": False}), ("cris_api", "cris_worker", {"apply": True})]
    monkeypatch.setattr(cli.database_security, "check_runtime", lambda engine, profile: {"verified": True, "profile": profile})
    monkeypatch.setattr(sys, "argv", ["enterprise", "database-check", "--database-profile", "api"])
    cli.main()
    assert json.loads(capsys.readouterr().out) == {"verified": True, "profile": "api"}


@pytest.mark.parametrize("command", ["migrate", "bootstrap", "backup", "database-harden"])
def test_runtime_profile_refuses_operator_cli_commands(store, monkeypatch, command):
    monkeypatch.setenv("CRIS_ENTERPRISE_DATABASE_URL", "postgresql+psycopg://fixture")
    monkeypatch.setenv("CRIS_ENTERPRISE_ENCRYPTION_KEY", "fixture")
    monkeypatch.setattr(cli.Store, "connect", lambda *args: store)
    store.database_profile = "api"
    monkeypatch.setattr(sys, "argv", ["enterprise", command])
    with pytest.raises(SystemExit):
        cli.main()


@pytest.mark.parametrize("args", [["database-harden"], ["database-check"]])
def test_database_cli_requires_explicit_roles_and_profile(store, monkeypatch, args):
    monkeypatch.setenv("CRIS_ENTERPRISE_DATABASE_URL", "postgresql+psycopg://fixture")
    monkeypatch.setenv("CRIS_ENTERPRISE_ENCRYPTION_KEY", "fixture")
    monkeypatch.setattr(cli.Store, "connect", lambda *args: store)
    monkeypatch.setattr(sys, "argv", ["enterprise", *args])
    with pytest.raises(SystemExit):
        cli.main()


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


def test_storage_cli_checks_inventory_preview_and_explicit_copy(context, tmp_path, monkeypatch, capsys):
    import json
    from tests.enterprise.test_storage import remote
    ctx = context
    monkeypatch.setenv("CRIS_ENTERPRISE_DATABASE_URL", "postgresql+psycopg://fixture")
    monkeypatch.setenv("CRIS_ENTERPRISE_ENCRYPTION_KEY", "fixture")
    monkeypatch.setenv("CRIS_ENTERPRISE_OIDC_ISSUER", ISSUER)
    monkeypatch.setenv("CRIS_ENTERPRISE_ARTIFACT_ROOT", str(ctx["root"]))
    monkeypatch.setattr(cli.Store, "connect", lambda *args: ctx["store"])
    transport = remote()
    monkeypatch.setattr(cli, "configured_storage", lambda root: transport)
    for command in ["storage-check", "storage-copy", "storage-usage", "retention-plan"]:
        args = ["enterprise", command, "--tenant", ctx["tenant"], "--subject", "owner"]
        if command == "retention-plan":
            args += ["--retention-days", "30"]
        monkeypatch.setattr(sys, "argv", args)
        cli.main()
        result = json.loads(capsys.readouterr().out)
        assert result.get("deletion_executed", False) is False
    monkeypatch.setattr(sys, "argv", args + ["--apply"])
    with pytest.raises(SystemExit):
        cli.main()


@pytest.mark.parametrize("command", ["storage-usage", "retention-plan"])
def test_metadata_storage_commands_never_load_cloud_credentials(store, monkeypatch, command):
    monkeypatch.setenv("CRIS_ENTERPRISE_DATABASE_URL", "postgresql+psycopg://fixture")
    monkeypatch.setenv("CRIS_ENTERPRISE_ENCRYPTION_KEY", "fixture")
    monkeypatch.setattr(cli.Store, "connect", lambda *args: store)
    monkeypatch.setattr(cli, "configured_storage", lambda root: pytest.fail("Metadata preview must not contact storage"))
    monkeypatch.setattr(sys, "argv", ["enterprise", command])
    with pytest.raises(SystemExit):
        cli.main()


def test_retention_cli_requires_feature_gate_and_explicit_apply(context, monkeypatch, capsys):
    import json
    from tests.enterprise.test_retention import eligible, cooled
    ctx = context
    eligible(ctx)
    ctx["store"].member(ctx["tenant"], ctx["principal"], "second-owner", "owner")
    for name, value in {"DATABASE_URL": "postgresql+psycopg://fixture", "ENCRYPTION_KEY": "fixture",
                        "OIDC_ISSUER": ISSUER, "ARTIFACT_ROOT": str(ctx["root"])}.items():
        monkeypatch.setenv("CRIS_ENTERPRISE_" + name, value)
    monkeypatch.setattr(cli.Store, "connect", lambda *args: ctx["store"])
    base = ["--tenant", ctx["tenant"], "--subject", "owner"]
    proposal = ["enterprise", "retention-propose", *base, "--retention-days", "30", "--reason", "Approved test policy", "--apply"]
    monkeypatch.setattr(sys, "argv", proposal)
    monkeypatch.delenv("CRIS_ENTERPRISE_RETENTION_ENABLED", raising=False)
    with pytest.raises(SystemExit):
        cli.main()
    monkeypatch.setenv("CRIS_ENTERPRISE_RETENTION_ENABLED", "true")
    cli.main()
    plan = json.loads(capsys.readouterr().out)
    identity = ["--tenant", ctx["tenant"], "--subject", "second-owner", "--plan", plan["id"], "--plan-sha256", plan["sha256"], "--apply"]
    monkeypatch.setattr(sys, "argv", ["enterprise", "retention-approve", *identity])
    cli.main()
    assert json.loads(capsys.readouterr().out)["state"] == "approved"
    cooled(ctx, plan)
    monkeypatch.setattr(sys, "argv", ["enterprise", "retention-expire", *identity])
    cli.main()
    assert json.loads(capsys.readouterr().out)["state"] == "expired"
    monkeypatch.setattr(sys, "argv", ["enterprise", "retention-cleanup", *identity])
    cli.main()
    assert json.loads(capsys.readouterr().out)["quarantined"] == 2


@pytest.mark.parametrize("command", ["retention-hold", "retention-propose", "retention-approve", "retention-withdraw", "retention-expire", "retention-cleanup"])
def test_retention_mutations_never_apply_by_default(store, monkeypatch, command):
    monkeypatch.setenv("CRIS_ENTERPRISE_DATABASE_URL", "postgresql+psycopg://fixture")
    monkeypatch.setenv("CRIS_ENTERPRISE_ENCRYPTION_KEY", "fixture")
    monkeypatch.setattr(cli.Store, "connect", lambda *args: store)
    monkeypatch.setattr(sys, "argv", ["enterprise", command])
    with pytest.raises(SystemExit):
        cli.main()


def test_operator_status_and_limit_configuration(context, monkeypatch, capsys):
    import json
    ctx = context
    for name, value in {"DATABASE_URL": "postgresql+psycopg://fixture", "ENCRYPTION_KEY": "fixture",
                        "ARTIFACT_ROOT": str(ctx["root"]), "OIDC_ISSUER": ISSUER}.items():
        monkeypatch.setenv("CRIS_ENTERPRISE_" + name, value)
    monkeypatch.setattr(cli.Store, "connect", lambda *args: ctx["store"])
    monkeypatch.setattr(sys, "argv", ["enterprise", "operations-status"])
    cli.main()
    assert json.loads(capsys.readouterr().out)["redacted"] is True
    arguments = ["enterprise", "operations-limits", "--tenant", ctx["tenant"], "--subject", "owner",
                 "--quota-bytes", str(256 * 1024 * 1024), "--max-artifacts", "100"]
    monkeypatch.setattr(sys, "argv", arguments)
    with pytest.raises(SystemExit):
        cli.main()
    monkeypatch.setattr(sys, "argv", arguments + ["--apply"])
    cli.main()
    assert json.loads(capsys.readouterr().out)["max_artifacts"] == 100
