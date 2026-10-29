"""Explicit migration/bootstrap/server/worker commands for the enterprise path."""
import argparse
import json
import os
from pathlib import Path
from uuid import UUID

from cris_sme.enterprise.api import Settings, create_app
from cris_sme.enterprise.auth import Principal
from cris_sme.enterprise.schema import migrate
from cris_sme.enterprise.store import Store
from cris_sme.enterprise.worker import run_worker
from cris_sme.enterprise.historical import prepare_import, publish_import
from cris_sme.enterprise.recovery import backup, inspect_backup, restore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["migrate", "bootstrap", "serve", "worker", "historical-import", "backup", "check-backup", "restore"])
    parser.add_argument("--name")
    parser.add_argument("--subject")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8788)
    parser.add_argument("--tenant", type=UUID)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--report", type=Path, action="append")
    parser.add_argument("--include-exports", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-dir", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    store = Store.connect(os.environ["CRIS_ENTERPRISE_DATABASE_URL"], os.environ["CRIS_ENTERPRISE_ENCRYPTION_KEY"])
    if args.command == "migrate":
        migrate(store.engine)
        return
    store.check_schema()
    root = Path(os.environ.get("CRIS_ENTERPRISE_ARTIFACT_ROOT", "outputs/enterprise-artifacts")).resolve()
    if args.command in {"backup", "check-backup", "restore"}:
        if not args.backup_dir:
            parser.error("Recovery commands require --backup-dir")
        if args.command == "backup":
            result = backup(store, root, args.backup_dir)
        elif args.command == "restore":
            if not args.apply:
                parser.error("Restore requires --apply and an empty isolated target")
            result = restore(store, args.backup_dir, root)
        else:
            tables = inspect_backup(store, args.backup_dir)
            result = {"verified": True, "artifacts": len(tables["cris_artifacts"])}
        print(json.dumps(result))
    elif args.command == "bootstrap":
        if not args.name or not args.subject:
            parser.error("bootstrap requires --name and --subject")
        print(store.bootstrap(Principal(os.environ["CRIS_ENTERPRISE_OIDC_ISSUER"], args.subject), args.name))
    elif args.command == "historical-import":
        if not args.tenant or not args.subject or not args.source_root or not args.report or len(args.report) > 20:
            parser.error("historical-import requires --tenant, --subject, --source-root and 1-20 --report paths")
        principal = Principal(os.environ["CRIS_ENTERPRISE_OIDC_ISSUER"], args.subject)
        with store.engine.connect() as connection:
            store._access(connection, str(args.tenant), principal, {"owner", "admin"})
        prepared = [prepare_import(args.source_root, report, include_exports=args.include_exports) for report in args.report]
        for report in prepared:
            result = publish_import(store, str(args.tenant), principal, report, root) if args.apply else {"dry_run": True}
            print(json.dumps({**report.preview(), **result}))
    elif args.command == "worker":
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        run_worker(store, root)
    else:
        import uvicorn
        settings = Settings(issuer=os.environ["CRIS_ENTERPRISE_OIDC_ISSUER"],
            audience=os.environ["CRIS_ENTERPRISE_OIDC_AUDIENCE"], jwks_url=os.environ["CRIS_ENTERPRISE_JWKS_URL"],
            client_id=os.environ["CRIS_ENTERPRISE_OIDC_CLIENT_ID"], authorization_url=os.environ["CRIS_ENTERPRISE_AUTHORIZE_URL"],
            token_url=os.environ["CRIS_ENTERPRISE_TOKEN_URL"], artifact_root=root,
            aws_principal_arn=os.environ.get("CRIS_ENTERPRISE_AWS_PRINCIPAL_ARN", ""),
            oidc_ca_file=os.environ.get("CRIS_ENTERPRISE_OIDC_CA_FILE"),
            allowed_hosts=tuple(os.environ.get("CRIS_ENTERPRISE_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")))
        uvicorn.run(create_app(settings, store), host=args.host, port=args.port, limit_concurrency=32,
                    timeout_keep_alive=5, access_log=False)


if __name__ == "__main__":
    main()
