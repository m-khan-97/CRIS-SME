"""Explicit dedicated-database grants and tenant RLS defense in depth.

Transaction context is supplied by the trusted API, not authenticated by PostgreSQL.
These policies catch missing filters; they do not contain arbitrary SQL execution
or a compromised service credential. Workers intentionally span tenants.
"""
import re
import json

from sqlalchemy import text

from cris_sme.enterprise import schema as s


API = {
    "cris_tenants": {"SELECT"}, "cris_memberships": {"SELECT", "INSERT", "DELETE"},
    "cris_connections": {"SELECT", "INSERT", "UPDATE"}, "cris_jobs": {"SELECT", "INSERT", "UPDATE"},
    "cris_artifacts": {"SELECT"}, "cris_audit": {"SELECT", "INSERT"},
    "cris_historical_imports": {"SELECT"}, "cris_retention_holds": {"SELECT", "INSERT", "UPDATE"},
    "cris_retention_hold_events": {"SELECT", "INSERT"}, "cris_retention_plans": {"SELECT", "INSERT", "UPDATE"},
    "cris_retirements": {"SELECT"}, "cris_retention_cleanup": {"SELECT"},
    "cris_tenant_limits": {"SELECT"}, "cris_action_rates": {"SELECT", "INSERT", "UPDATE"},
    "cris_worker_health": set(), "cris_schema_version": {"SELECT"},
}
WORKER = {name: {"SELECT"} for name in API}
WORKER.update({"cris_jobs": {"SELECT", "UPDATE"}, "cris_artifacts": {"SELECT", "INSERT"},
               "cris_audit": {"INSERT"}, "cris_worker_health": {"SELECT", "INSERT", "UPDATE", "DELETE"},
               "cris_action_rates": set()})
PROFILES = {"api": API, "worker": WORKER}
LOCK_COLUMNS = {"api": {"cris_tenants": {"id"}},
                "worker": {"cris_tenants": {"id"}, "cris_connections": {"id"}}}
POLICIES = {"cris_api_select", "cris_api_insert", "cris_api_update", "cris_api_delete", "cris_worker", "cris_operator"}
CONTEXT_SQL = text("SELECT set_config('cris.tenant_id', :tenant, true), "
                   "set_config('cris.issuer', :issuer, true), set_config('cris.subject', :subject, true)")


def request_context(connection, principal, tenant=""):
    connection.execute(CONTEXT_SQL, {"tenant": tenant, "issuer": principal.issuer, "subject": principal.subject})


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", value):
        raise ValueError("Use a simple lowercase PostgreSQL role/schema identifier")
    return '"' + value + '"'


def namespace(connection):
    return connection.schema_for_object(s.jobs) or connection.execute(text("SELECT current_schema()")).scalar_one()


def _relations(connection, schema):
    return {row["relname"]: row for row in connection.execute(text(
        "SELECT t.oid, t.relname, t.relrowsecurity, t.relforcerowsecurity, r.rolname AS owner "
        "FROM pg_class t JOIN pg_namespace n ON n.oid=t.relnamespace "
        "JOIN pg_roles r ON r.oid=t.relowner WHERE n.nspname=:schema AND t.relkind='r'"),
        {"schema": schema}).mappings()}


def _role(connection, role, schema, relations):
    identifier(role)
    row = connection.execute(text("SELECT oid, rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, "
        "rolreplication, rolbypassrls FROM pg_roles WHERE rolname=:role"), {"role": role}).mappings().first()
    if row is None or not row["rolcanlogin"] or any(row[key] for key in (
            "rolsuper", "rolcreatedb", "rolcreaterole", "rolreplication", "rolbypassrls")):
        raise ValueError("Runtime roles must be existing, unprivileged LOGIN roles")
    if connection.execute(text("SELECT 1 FROM pg_auth_members WHERE member=:oid LIMIT 1"), {"oid": row["oid"]}).first():
        raise ValueError("Use dedicated runtime roles without other role memberships")
    if role in {item["owner"] for item in relations.values()} or connection.execute(text(
            "SELECT 1 FROM pg_database WHERE datname=current_database() AND datdba=:oid"), {"oid": row["oid"]}).first():
        raise ValueError("Runtime roles must not own application tables or the database")
    if connection.execute(text("SELECT 1 FROM pg_namespace WHERE nspname=:schema AND nspowner=:oid"),
                          {"schema": schema, "oid": row["oid"]}).first():
        raise ValueError("Runtime roles must not own the application schema")
    return row


def _coverage(relations):
    if set(s.metadata.tables) != set(API) or not set(API) <= set(relations):
        raise ValueError("Database security manifest does not cover the current schema")


def harden(engine, api_role, worker_role, *, apply=False):
    """Apply grants/policies atomically, only after explicit operator confirmation."""
    api, worker = identifier(api_role), identifier(worker_role)
    if api_role == worker_role:
        raise ValueError("API and worker require different database roles")
    with engine.begin() as c:
        c.execute(text("SELECT pg_advisory_xact_lock(754392810)"))
        schema = namespace(c)
        quoted = identifier(schema)
        relations = _relations(c, schema)
        _coverage(relations)
        for role in (api_role, worker_role):
            _role(c, role, schema, relations)
        policies = list(c.execute(text("SELECT p.polname FROM pg_policy p JOIN pg_class t ON t.oid=p.polrelid "
            "JOIN pg_namespace n ON n.oid=t.relnamespace WHERE n.nspname=:schema AND t.relname = ANY(:tables)"),
            {"schema": schema, "tables": list(API)}).scalars())
        if set(policies) - POLICIES:
            raise ValueError("Unexpected row policies; review them before applying CRIS hardening")
        result = {"applied": apply, "schema": schema, "api_role": api_role, "worker_role": worker_role,
                  "tables": len(API), "row_policy_tables": len(API) - 1, "schema_version": s.SCHEMA_VERSION}
        if not apply:
            return result
        # This is an explicit dedicated-schema operation, not a shared-database migration.
        c.exec_driver_sql(f"REVOKE CREATE ON SCHEMA {quoted} FROM PUBLIC, {api}, {worker}")
        c.exec_driver_sql(f"GRANT USAGE ON SCHEMA {quoted} TO {api}, {worker}")
        for name in API:
            table = quoted + "." + identifier(name)
            c.exec_driver_sql(f"REVOKE ALL PRIVILEGES ON TABLE {table} FROM PUBLIC, {api}, {worker}")
            columns = ", ".join(identifier(column.name) for column in s.metadata.tables[name].columns)
            column_grants = ", ".join(f"{privilege} ({columns})" for privilege in ("SELECT", "INSERT", "UPDATE", "REFERENCES"))
            c.exec_driver_sql(f"REVOKE {column_grants} ON TABLE {table} FROM PUBLIC, {api}, {worker}")
            for role, grants in ((api, API[name]), (worker, WORKER[name])):
                if grants:
                    c.exec_driver_sql(f"GRANT {', '.join(sorted(grants))} ON TABLE {table} TO {role}")
            if name == "cris_schema_version":
                continue
            for policy in POLICIES:
                c.exec_driver_sql(f"DROP POLICY IF EXISTS {identifier(policy)} ON {table}")
            column = "id" if name == "cris_tenants" else "tenant_id"
            scope = f"{column} = NULLIF(current_setting('cris.tenant_id', true), '')" if name != "cris_worker_health" else "false"
            discovery = ("issuer = NULLIF(current_setting('cris.issuer', true), '') AND "
                         "subject = NULLIF(current_setting('cris.subject', true), '')")
            read = scope
            if name == "cris_memberships":
                read = f"({scope}) OR ({discovery})"
            elif name == "cris_tenants":
                read = f"({scope}) OR EXISTS (SELECT 1 FROM {quoted}.cris_memberships m WHERE m.tenant_id = id AND {discovery})"
            if "SELECT" in API[name]:
                c.exec_driver_sql(f"CREATE POLICY cris_api_select ON {table} FOR SELECT TO {api} USING ({read})")
            for command in ("INSERT", "UPDATE", "DELETE"):
                if command in API[name] or (name == "cris_tenants" and command == "UPDATE"):
                    using = f"USING ({scope})" if command != "INSERT" else ""
                    check = f"WITH CHECK ({scope})" if command != "DELETE" else ""
                    c.exec_driver_sql(f"CREATE POLICY cris_api_{command.lower()} ON {table} FOR {command} TO {api} {using} {check}")
            if WORKER[name]:
                c.exec_driver_sql(f"CREATE POLICY cris_worker ON {table} TO {worker} USING (true) WITH CHECK (true)")
            owner = identifier(relations[name]["owner"])
            c.exec_driver_sql(f"CREATE POLICY cris_operator ON {table} TO {owner} USING (true) WITH CHECK (true)")
            c.exec_driver_sql(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            c.exec_driver_sql(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        # SELECT FOR UPDATE used by admission requires one column's UPDATE privilege.
        c.exec_driver_sql(f"GRANT UPDATE (id) ON TABLE {quoted}.cris_tenants TO {api}, {worker}")
        c.exec_driver_sql(f"GRANT UPDATE (id) ON TABLE {quoted}.cris_connections TO {worker}")
        return result


def check_runtime(engine, profile):
    if profile not in PROFILES:
        raise ValueError("Choose the api or worker database profile")
    with engine.connect() as c:
        schema = namespace(c)
        relations = _relations(c, schema)
        _coverage(relations)
        role = c.execute(text("SELECT current_user")).scalar_one()
        account = _role(c, role, schema, relations)
        if not c.execute(text("SELECT has_schema_privilege(current_user, :schema, 'USAGE')"), {"schema": schema}).scalar_one():
            raise ValueError("Runtime credentials require application schema USAGE")
        if c.execute(text("SELECT has_schema_privilege(current_user, :schema, 'CREATE') "
                          "OR has_database_privilege(current_user, current_database(), 'CREATE')"), {"schema": schema}).scalar_one():
            raise ValueError("Runtime credentials must not have schema/database CREATE privileges")
        table_checks, column_checks = [], []
        policy_rows = c.execute(text("SELECT polrelid, polname FROM pg_policy WHERE "
            "polrelid = ANY(:tables) AND (:role = ANY(polroles) OR 0 = ANY(polroles))"),
            {"tables": [relations[name]["oid"] for name in API], "role": account["oid"]}).all()
        for name, allowed in PROFILES[profile].items():
            relation = relations[name]
            if name != "cris_schema_version" and not (relation["relrowsecurity"] and relation["relforcerowsecurity"]):
                raise ValueError("Required row security is not enabled and forced")
            reference = identifier(schema) + "." + identifier(name)
            for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"):
                table_checks.append({"relation": reference, "privilege": privilege, "expected": privilege in allowed})
            expected = set()
            if name != "cris_schema_version":
                if profile == "api":
                    expected = {"cris_api_" + item.lower() for item in allowed}
                    if name == "cris_tenants":
                        expected.add("cris_api_update")
                elif allowed:
                    expected = {"cris_worker"}
                actual = {row.polname for row in policy_rows if row.polrelid == relation["oid"]}
                if actual != expected:
                    raise ValueError("Runtime row policies do not match the selected profile")
            for column in s.metadata.tables[name].columns:
                for privilege in ("SELECT", "INSERT", "UPDATE", "REFERENCES"):
                    permitted = privilege in allowed or (
                        privilege == "UPDATE" and column.name in LOCK_COLUMNS[profile].get(name, set()))
                    column_checks.append({"relation": reference, "attribute": column.name,
                                          "privilege": privilege, "expected": permitted})
        # Set-based privilege checks keep readiness bounded in database round trips.
        for kind, checks, function, fields in (
            ("table", table_checks, "has_table_privilege(current_user, relation, privilege)", ""),
            ("column", column_checks, "has_column_privilege(current_user, relation, attribute, privilege)", "attribute text,"),
        ):
            mismatch = c.execute(text(f"SELECT EXISTS (SELECT 1 FROM jsonb_to_recordset(CAST(:checks AS jsonb)) "
                f"AS entry(relation text, {fields} privilege text, expected boolean) WHERE {function} IS DISTINCT FROM expected)"),
                {"checks": json.dumps(checks)}).scalar_one()
            if mismatch:
                raise ValueError(f"Runtime {kind} privileges do not match the selected profile")
        return {"verified": True, "profile": profile, "tables": len(API), "row_policy_tables": len(API) - 1}
