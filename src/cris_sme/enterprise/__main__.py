"""Explicit migration/bootstrap/server/worker commands for the enterprise path."""
import argparse
import os
from pathlib import Path

from cris_sme.enterprise.api import Settings, create_app
from cris_sme.enterprise.auth import Principal
from cris_sme.enterprise.schema import migrate
from cris_sme.enterprise.store import Store
from cris_sme.enterprise.worker import run_worker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["migrate", "bootstrap", "serve", "worker"])
    parser.add_argument("--name")
    parser.add_argument("--subject")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8788)
    args = parser.parse_args()
    os.umask(0o077)
    store = Store.connect(os.environ["CRIS_ENTERPRISE_DATABASE_URL"], os.environ["CRIS_ENTERPRISE_ENCRYPTION_KEY"])
    if args.command == "migrate":
        migrate(store.engine)
        return
    store.check_schema()
    root = Path(os.environ.get("CRIS_ENTERPRISE_ARTIFACT_ROOT", "outputs/enterprise-artifacts")).resolve()
    if args.command == "bootstrap":
        if not args.name or not args.subject:
            parser.error("bootstrap requires --name and --subject")
        print(store.bootstrap(Principal(os.environ["CRIS_ENTERPRISE_OIDC_ISSUER"], args.subject), args.name))
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
            allowed_hosts=tuple(os.environ.get("CRIS_ENTERPRISE_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")))
        uvicorn.run(create_app(settings, store), host=args.host, port=args.port, limit_concurrency=32,
                    timeout_keep_alive=5, access_log=False)


if __name__ == "__main__":
    main()
