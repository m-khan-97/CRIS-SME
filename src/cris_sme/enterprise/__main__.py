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
from cris_sme.enterprise.storage import configured_storage, LocalStorage, S3Storage
from cris_sme.enterprise.storage_operations import copy_registered, retention_plan, usage
from cris_sme.enterprise import retention
from cris_sme.enterprise import operations
from cris_sme.enterprise import database_security


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["migrate", "bootstrap", "serve", "worker", "historical-import", "backup", "check-backup", "restore", "storage-check", "storage-copy", "storage-usage", "retention-plan", "retention-hold", "retention-propose", "retention-approve", "retention-withdraw", "retention-expire", "retention-cleanup", "operations-status", "operations-limits", "database-harden", "database-check"])
    parser.add_argument("--api-role")
    parser.add_argument("--worker-role")
    parser.add_argument("--database-profile", choices=["api", "worker"])
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
    parser.add_argument("--retention-days", type=int)
    parser.add_argument("--exclude-job", type=UUID, action="append", default=[])
    parser.add_argument("--include-historical", action="store_true")
    parser.add_argument("--assessment", type=UUID)
    parser.add_argument("--plan", type=UUID)
    parser.add_argument("--plan-sha256")
    parser.add_argument("--reason")
    parser.add_argument("--release", action="store_true")
    parser.add_argument("--quota-bytes", type=int)
    parser.add_argument("--max-artifacts", type=int)
    args = parser.parse_args()
    os.umask(0o077)
    store = Store.connect(os.environ["CRIS_ENTERPRISE_DATABASE_URL"], os.environ["CRIS_ENTERPRISE_ENCRYPTION_KEY"])
    if args.command == "database-check":
        if not args.database_profile:
            parser.error("database-check requires --database-profile api or worker")
        print(json.dumps(database_security.check_runtime(store.engine, args.database_profile)))
        return
    if args.command not in {"serve", "worker"} and store.database_profile != "development":
        parser.error("Operator commands require separate migration/operator credentials, not a runtime profile")
    if args.command == "migrate":
        migrate(store.engine)
        return
    store.check_schema()
    if args.command == "database-harden":
        if not args.api_role or not args.worker_role:
            parser.error("database-harden requires --api-role and --worker-role")
        print(json.dumps(database_security.harden(store.engine, args.api_role, args.worker_role, apply=args.apply)))
        return
    root = Path(os.environ.get("CRIS_ENTERPRISE_ARTIFACT_ROOT", "outputs/enterprise-artifacts")).resolve()
    storage = configured_storage(root) if args.command in {
        "serve", "worker", "historical-import", "backup", "restore", "storage-check", "storage-copy", "retention-expire", "retention-cleanup"
    } else LocalStorage(root)
    if args.command == "operations-status":
        print(json.dumps(operations.operator_status(store, root)))
    elif args.command == "operations-limits":
        if not args.apply or not args.tenant or not args.subject or args.quota_bytes is None or args.max_artifacts is None:
            parser.error("Limit changes require --apply, --tenant, --subject, --quota-bytes and --max-artifacts")
        actor = Principal(os.environ["CRIS_ENTERPRISE_OIDC_ISSUER"], args.subject)
        print(json.dumps(operations.set_limits(store, str(args.tenant), actor, args.quota_bytes, args.max_artifacts)))
    elif args.command in {"retention-hold", "retention-propose", "retention-approve", "retention-withdraw", "retention-expire", "retention-cleanup"}:
        if not args.tenant or not args.subject or not args.apply:
            parser.error("Retention mutations require --tenant, --subject and explicit --apply")
        if args.command not in {"retention-hold", "retention-withdraw"} and os.environ.get("CRIS_ENTERPRISE_RETENTION_ENABLED") != "true":
            parser.error("Retention mutation execution is disabled")
        principal = Principal(os.environ["CRIS_ENTERPRISE_OIDC_ISSUER"], args.subject)
        if args.command == "retention-hold":
            if not args.assessment or not args.reason:
                parser.error("Hold changes require --assessment and --reason")
            result = retention.hold(store, str(args.tenant), principal, str(args.assessment), args.reason, active=not args.release)
        elif args.command == "retention-propose":
            if args.retention_days is None or not args.reason:
                parser.error("Proposals require --retention-days and --reason")
            result = retention.propose(store, str(args.tenant), principal, args.retention_days, args.reason,
                exclude=[str(value) for value in args.exclude_job], include_historical=args.include_historical)
        else:
            if not args.plan or (args.command != "retention-cleanup" and not args.plan_sha256):
                parser.error("A --plan and --plan-sha256 are required")
            if args.command in {"retention-approve", "retention-withdraw"}:
                result = retention.decide(store, str(args.tenant), principal, str(args.plan), args.plan_sha256,
                                          approve=args.command == "retention-approve")
            elif args.command == "retention-expire":
                result = retention.expire(store, str(args.tenant), principal, str(args.plan), args.plan_sha256, storage)
            else:
                result = retention.cleanup_local(store, str(args.tenant), principal, str(args.plan), storage)
        print(json.dumps(result))
    elif args.command in {"storage-usage", "retention-plan"}:
        if not args.tenant or not args.subject:
            parser.error("Storage inventory requires --tenant and --subject")
        principal = Principal(os.environ["CRIS_ENTERPRISE_OIDC_ISSUER"], args.subject)
        if args.command == "retention-plan":
            if args.retention_days is None or args.apply:
                parser.error("Retention preview requires --retention-days; --apply is not supported")
            result = retention_plan(store, str(args.tenant), principal, args.retention_days,
                                    exclude=[str(value) for value in args.exclude_job], include_historical=args.include_historical)
        else:
            result = usage(store, str(args.tenant), principal)
        print(json.dumps(result))
    elif args.command == "storage-check":
        storage.check_ready()
        print(json.dumps({"ready": True, "backend": "s3" if isinstance(storage, S3Storage) else "local"}))
    elif args.command == "storage-copy":
        if not isinstance(storage, S3Storage):
            parser.error("Storage copy requires an explicitly configured S3 destination")
        print(json.dumps(copy_registered(store, root, storage, apply=args.apply)))
    elif args.command in {"backup", "check-backup", "restore"}:
        if not args.backup_dir:
            parser.error("Recovery commands require --backup-dir")
        if args.command == "backup":
            result = backup(store, root, args.backup_dir, storage=storage)
        elif args.command == "restore":
            if not args.apply:
                parser.error("Restore requires --apply and an empty isolated target")
            result = restore(store, args.backup_dir, root, storage=storage)
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
            result = publish_import(store, str(args.tenant), principal, report, root, storage=storage) if args.apply else {"dry_run": True}
            print(json.dumps({**report.preview(), **result}))
    elif args.command == "worker":
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        storage.check_ready()
        run_worker(store, root, storage)
    else:
        import uvicorn
        settings = Settings(issuer=os.environ["CRIS_ENTERPRISE_OIDC_ISSUER"],
            audience=os.environ["CRIS_ENTERPRISE_OIDC_AUDIENCE"], jwks_url=os.environ["CRIS_ENTERPRISE_JWKS_URL"],
            client_id=os.environ["CRIS_ENTERPRISE_OIDC_CLIENT_ID"], authorization_url=os.environ["CRIS_ENTERPRISE_AUTHORIZE_URL"],
            token_url=os.environ["CRIS_ENTERPRISE_TOKEN_URL"], artifact_root=root,
            aws_principal_arn=os.environ.get("CRIS_ENTERPRISE_AWS_PRINCIPAL_ARN", ""),
            oidc_ca_file=os.environ.get("CRIS_ENTERPRISE_OIDC_CA_FILE"),
            allowed_hosts=tuple(os.environ.get("CRIS_ENTERPRISE_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")),
            artifact_storage=storage, retention_enabled=os.environ.get("CRIS_ENTERPRISE_RETENTION_ENABLED") == "true")
        uvicorn.run(create_app(settings, store), host=args.host, port=args.port, limit_concurrency=32,
                    timeout_keep_alive=5, access_log=False)


if __name__ == "__main__":
    main()
