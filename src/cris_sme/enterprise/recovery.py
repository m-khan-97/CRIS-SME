"""Bounded, offline logical recovery bundles. Not a substitute for PostgreSQL PITR."""
import hashlib
import json
import os
from pathlib import Path
import re
from uuid import UUID

from sqlalchemy import insert, select

from cris_sme.api.artifact_access import MAX_ARTIFACT_BYTES, read_regular_file
from cris_sme.enterprise import schema as s
from cris_sme.enterprise.historical import unique_object, reject_constant
from cris_sme.enterprise.storage import LocalStorage, S3Storage

TABLES = tuple(table for table in s.metadata.sorted_tables if table is not s.versions)
V3_TABLES = (s.holds, s.hold_events, s.retention_plans, s.retirements, s.cleanup)
MAX_METADATA = 16 * 1024 * 1024
MAX_BYTES = 512 * 1024 * 1024
MAX_ROWS = 100_000
MAX_FILES = 10_000
TERMINAL = {"completed", "failed", "cancelled"}


def quarantine_key(artifact, retired):
    return str(Path("retention_quarantine") / artifact["tenant_id"] / retired["plan_id"] / artifact["id"])


def _hash(content):
    return hashlib.sha256(content).hexdigest()


def _lock(connection):
    # Translate schema names explicitly for isolated test/restore schemas.
    quote = connection.dialect.identifier_preparer.quote
    names = []
    for table in s.metadata.sorted_tables:
        schema = connection.schema_for_object(table)
        names.append((quote(schema) + "." if schema else "") + quote(table.name))
    connection.exec_driver_sql("LOCK TABLE " + ", ".join(names) + " IN SHARE ROW EXCLUSIVE MODE NOWAIT")
    if list(connection.execute(select(s.versions.c.version)).scalars()) != [s.SCHEMA_VERSION]:
        raise ValueError("Migrate to the supported schema before recovery operations")


def _rows(connection):
    result = {}
    remaining = MAX_ROWS
    for table in TABLES:
        rows = [dict(row) for row in connection.execute(select(table).limit(remaining + 1)).mappings()]
        remaining -= len(rows)
        if remaining < 0:
            raise ValueError("Recovery row limit exceeded")
        result[table.name] = rows
    return result


def _validate(tables, cipher):
    if not isinstance(tables, dict) or set(tables) != {t.name for t in TABLES}:
        raise ValueError("Unsupported recovery tables")
    if any(not isinstance(rows, list) for rows in tables.values()) or sum(map(len, tables.values())) > MAX_ROWS:
        raise ValueError("Recovery row limit exceeded")
    for table in TABLES:
        for row in tables[table.name]:
            if not isinstance(row, dict) or set(row) != set(table.c.keys()):
                raise ValueError("Unsupported recovery row shape")
    for row in tables[s.connections.name]:
        cipher.decrypt(row["secret"].encode())
    jobs = {(row["tenant_id"], row["id"]): row for row in tables[s.jobs.name]}
    if any(row["status"] not in TERMINAL for row in jobs.values()):
        raise ValueError("Recovery requires all assessments to be terminal; stop admission and drain workers")
    plans = {row["id"]: row for row in tables[s.retention_plans.name]}
    for row in tables[s.retirements.name]:
        for key in ("tenant_id", "job_id", "plan_id"):
            if str(UUID(row[key])) != row[key]:
                raise ValueError("Invalid recovery quarantine identifier")
        plan = plans.get(row["plan_id"])
        if (row["tenant_id"], row["job_id"]) not in jobs or plan is None or plan["tenant_id"] != row["tenant_id"] or plan["state"] != "expired":
            raise ValueError("Invalid recovery quarantine scope")
    artifacts = tables[s.artifacts.name]
    if len(artifacts) > MAX_FILES:
        raise ValueError("Recovery artifact count exceeded")
    total, identifiers, keys = 0, set(), set()
    for row in artifacts:
        for key in ("id", "tenant_id", "job_id"):
            if str(UUID(row[key])) != row[key]:
                raise ValueError("Noncanonical recovery identifier")
        path = Path(row["key"])
        if path.is_absolute() or str(path) != row["key"] or any(part.startswith(".") for part in path.parts) or len(path.parts) < 3:
            raise ValueError("Invalid recovery artifact path")
        if path.parts[:2] != (row["tenant_id"], row["job_id"]) or path.name != row["name"]:
            raise ValueError("Recovery artifact namespace mismatch")
        if row["id"] in identifiers or row["key"] in keys:
            raise ValueError("Duplicate recovery artifact")
        identifiers.add(row["id"])
        keys.add(row["key"])
        job = jobs.get((row["tenant_id"], row["job_id"]))
        if job is None or job["status"] != "completed":
            raise ValueError("Recovery artifact requires its completed scoped assessment")
        size = row["size"]
        if isinstance(size, bool) or not isinstance(size, int) or not 0 <= size <= MAX_ARTIFACT_BYTES:
            raise ValueError("Invalid recovery artifact size")
        if not isinstance(row["sha256"], str) or not re.fullmatch("[0-9a-f]{64}", row["sha256"]):
            raise ValueError("Invalid recovery artifact digest")
        total += size
    if total > MAX_BYTES:
        raise ValueError("Recovery artifact byte limit exceeded")


def _write(path, content):
    with path.open("xb") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _checked(root, path, row):
    content = read_regular_file(root, path)
    if len(content) != row["size"] or _hash(content) != row["sha256"]:
        raise ValueError("Recovery artifact integrity check failed")
    return content


def backup(store, artifact_root: Path, destination: Path, *, storage=None):
    """Require an unused destination and a quiescent database; no credentials are decrypted to disk."""
    destination = destination.absolute()
    artifact_root = artifact_root.absolute()
    storage = storage or LocalStorage(artifact_root)
    if destination.resolve() == artifact_root.resolve() or artifact_root.resolve() in destination.resolve().parents:
        raise ValueError("Keep backups outside the artifact root")
    with store.engine.begin() as connection:
        _lock(connection)
        tables = _rows(connection)
        _validate(tables, store.cipher)
        payload = json.dumps({"format": 1, "schema_version": s.SCHEMA_VERSION, "tables": tables}, sort_keys=True).encode()
        if len(payload) > MAX_METADATA:
            raise ValueError("Recovery metadata limit exceeded")
        destination.mkdir(mode=0o700)
        directory = destination / "artifacts"
        directory.mkdir(mode=0o700)
        retired = {row["job_id"]: row for row in tables[s.retirements.name]}
        for row in tables[s.artifacts.name]:
            if row["job_id"] in retired:
                try:
                    content = _checked(artifact_root, Path(quarantine_key(row, retired[row["job_id"]])), row)
                except FileNotFoundError:
                    content = _checked(artifact_root, Path(row["key"]), row)
            else:
                content = storage.read(row["key"])
            if len(content) != row["size"] or _hash(content) != row["sha256"]:
                raise ValueError("Recovery artifact integrity check failed")
            _write(directory / row["id"], content)
        _write(destination / "metadata.json", payload)
        # Completion marker is written last. Hashes detect damage, not malicious replacement.
        _write(destination / "complete.json", json.dumps({"format": 1, "metadata_sha256": _hash(payload)}).encode())
    return {"artifacts": len(tables[s.artifacts.name]), "tenants": len(tables[s.tenants.name]), "schema_version": s.SCHEMA_VERSION}


def inspect_backup(store, source: Path):
    complete = json.loads(read_regular_file(source, Path("complete.json"), max_bytes=1024),
                          object_pairs_hook=unique_object, parse_constant=reject_constant)
    payload = read_regular_file(source, Path("metadata.json"), max_bytes=MAX_METADATA)
    if not isinstance(complete, dict) or complete.get("format") != 1 or complete.get("metadata_sha256") != _hash(payload):
        raise ValueError("Recovery metadata integrity check failed")
    metadata = json.loads(payload, object_pairs_hook=unique_object, parse_constant=reject_constant)
    if not isinstance(metadata, dict) or metadata.get("format") != 1 or metadata.get("schema_version") not in (2, s.SCHEMA_VERSION):
        raise ValueError("Unsupported recovery format or schema")
    tables = metadata.get("tables")
    if not isinstance(tables, dict):
        raise ValueError("Unsupported recovery tables")
    if metadata["schema_version"] == 2:
        for table in V3_TABLES:
            if table.name in tables:
                raise ValueError("V2 bundle must not contain V3 retention records")
            tables[table.name] = []
    _validate(tables, store.cipher)
    for row in tables[s.artifacts.name]:
        _checked(source, Path("artifacts") / row["id"], row)
    return tables


def restore(store, source: Path, artifact_root: Path, *, storage=None):
    """Restore into an empty isolated target only, with every cloud connection disabled."""
    tables = inspect_backup(store, source)
    artifact_root = artifact_root.absolute()
    storage = storage or LocalStorage(artifact_root)
    retired = {row["job_id"]: row for row in tables[s.retirements.name]}
    if retired and isinstance(storage, S3Storage):
        raise ValueError("Restore local quarantine history to local storage; remote quarantine is not qualified")
    source_path, target_path = source.resolve(), artifact_root.resolve()
    if target_path == source_path or source_path in target_path.parents or target_path in source_path.parents:
        raise ValueError("Restore storage must be separate from the backup")
    with store.engine.begin() as connection:
        _lock(connection)
        if any(connection.execute(select(table).limit(1)).first() is not None for table in TABLES):
            raise ValueError("Restore requires an empty isolated database")
        if isinstance(storage, S3Storage):
            storage.check_ready()
            storage.require_empty()
        artifact_root.mkdir(mode=0o700)
        for row in tables[s.artifacts.name]:
            path = artifact_root / (quarantine_key(row, retired[row["job_id"]]) if row["job_id"] in retired else row["key"])
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            content = _checked(source, Path("artifacts") / row["id"], row)
            _write(path, content)
            if row["job_id"] not in retired:
                storage.publish(row["key"], content)
        for table in TABLES:
            rows = tables[table.name]
            if table is s.connections:
                rows = [{**row, "enabled": False, "verified_until": 0} for row in rows]
            elif table is s.retention_plans:
                rows = [{**row, "state": "invalidated_restore"} if row["state"] in {"proposed", "approved"} else row for row in rows]
            elif table is s.cleanup:
                rows = [{**row, "state": "quarantined", "error_code": ""} for row in rows]
            if rows:
                connection.execute(insert(table), rows)
    return {"artifacts": len(tables[s.artifacts.name]), "tenants": len(tables[s.tenants.name]), "connections_disabled": True}
