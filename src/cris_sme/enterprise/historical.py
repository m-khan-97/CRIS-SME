"""Operator-only, explicit historical ownership mapping; no cloud collection."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re

from sqlalchemy import insert, or_, select

from cris_sme.api.artifact_access import MAX_ARTIFACT_BYTES, MAX_REPORT_BYTES, REPORT_FILES, read_regular_file
from cris_sme.enterprise import schema as s
from cris_sme.enterprise.store import ADMIN, Rejected, new_id
from cris_sme.enterprise.storage import LocalStorage


def digest(content):
    return hashlib.sha256(content).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON fields are not accepted")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("Non-finite JSON values are not accepted")


@dataclass(frozen=True)
class PreparedImport:
    source: str
    source_run_id: str
    source_organization_id: str
    organization_name: str
    generated_at: str
    epoch: int
    provider: str
    scope_id: str
    reported_source_type: str
    source_sha256: str
    bundle_sha256: str
    files: dict[str, bytes]
    skipped_exports: tuple[str, ...]

    def preview(self):
        return {key: getattr(self, key) for key in ("source", "source_run_id", "source_organization_id",
            "organization_name", "generated_at", "provider", "scope_id", "reported_source_type",
            "source_sha256", "bundle_sha256")} | {
                "artifacts": [{"name": name, "size": len(content), "sha256": digest(content)}
                              for name, content in sorted(self.files.items())],
                "skipped_exports": list(self.skipped_exports),
                "provenance_policy": "preserved_as_supplied_not_revalidated"}


def prepare_import(source_root: Path, relative: Path, *, include_exports=False):
    source_root = source_root.resolve()
    if not re.fullmatch(r"cris_sme_report(?:_[0-9]{8}T[0-9]{6}Z)?\.json", relative.name):
        raise ValueError("Select an explicit CRIS JSON report or history snapshot")
    raw = read_regular_file(source_root, relative, max_bytes=MAX_REPORT_BYTES)
    report = json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)
    if not isinstance(report, dict):
        raise ValueError("Expected a report object")
    organizations, run = report.get("organizations"), report.get("run_metadata")
    if not isinstance(organizations, list) or len(organizations) != 1 or not isinstance(organizations[0], dict) or not isinstance(run, dict):
        raise ValueError("Import requires one explicit source organization and run metadata")
    org = organizations[0]
    provider = org.get("provider")
    if provider not in {"aws", "azure"} or report.get("collector_mode") != provider or run.get("providers_in_scope") != [provider]:
        raise ValueError("Source provider scope is inconsistent or unsupported")
    run_id, org_id = run.get("run_id"), org.get("organization_id")
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", run_id):
        raise ValueError("A stable source run ID is required")
    if not isinstance(org_id, str) or not 1 <= len(org_id) <= 512:
        raise ValueError("A source organization ID is required")
    name = org.get("organization_name")
    if not isinstance(name, str) or not 1 <= len(name) <= 200:
        raise ValueError("A source organization name is required")
    generated = report.get("generated_at")
    if not isinstance(generated, str) or len(generated) > 80:
        raise ValueError("A source generation timestamp is required")
    observed = datetime.fromisoformat(generated)
    if observed.tzinfo is None or not 0 < observed.timestamp() <= datetime.now(timezone.utc).timestamp():
        raise ValueError("An aware historical generation timestamp is required")
    if run.get("generated_at") and datetime.fromisoformat(run["generated_at"]) != observed:
        raise ValueError("Conflicting generation timestamps")
    if not isinstance(report.get("prioritized_risks"), list) or not isinstance(report.get("resource_context"), dict) or not isinstance(report.get("assessment_runner"), dict):
        raise ValueError("Report sections required by the console are missing")
    details = org.get("collection_details") or {}
    if not isinstance(details, dict):
        raise ValueError("Invalid source collection details")
    scope_id = details.get("subscription_id") if provider == "azure" else details.get("account_id", org.get("tenant_scope", ""))
    if not isinstance(scope_id, str) or len(scope_id) > 36:
        raise ValueError("Invalid recorded cloud scope")
    source_type = details.get("dataset_source_type", "")
    if not isinstance(source_type, str) or len(source_type) > 200:
        raise ValueError("Invalid recorded source type")
    files = {"cris_sme_report.json": raw}
    skipped = []
    artifacts = report.get("report_artifacts") or {}
    if include_exports and relative.name == "cris_sme_report.json" and isinstance(artifacts, dict):
        def references(value):
            if isinstance(value, str):
                yield value
            elif isinstance(value, dict):
                for child in value.values():
                    yield from references(child)
        declared_json = artifacts.get("json_report")
        if declared_json:
            declared = Path(declared_json)
            if (declared if declared.is_absolute() else source_root / declared) != source_root / relative:
                raise ValueError("Report export inventory belongs to a different source path")
        for reference in sorted(set(references(artifacts))):
            candidate = Path(reference)
            if not candidate.is_absolute():
                candidate = source_root / candidate
            # Never dereference arbitrary paths from report JSON or pair an old
            # snapshot with the latest exports beside its parent directory.
            if candidate.parent != source_root / relative.parent or candidate.name not in REPORT_FILES or candidate.name in files:
                continue
            try:
                content = read_regular_file(source_root, relative.parent / candidate.name, max_bytes=MAX_ARTIFACT_BYTES)
            except FileNotFoundError:
                skipped.append(candidate.name)
                continue
            files[candidate.name] = content
            if len(files) > 64 or sum(map(len, files.values())) > 128 * 1024 * 1024:
                raise ValueError("Historical export bundle exceeds import limits")
    bundle = digest(json.dumps({name: digest(content) for name, content in sorted(files.items())}, sort_keys=True).encode())
    return PreparedImport(str(relative), run_id, org_id, name, generated, int(observed.timestamp()), provider,
                          scope_id or "", source_type, digest(raw), bundle, files, tuple(skipped))


def publish_import(store, tenant, principal, prepared: PreparedImport, artifact_root: Path, *, storage=None):
    """Files precede one metadata transaction; interrupted copies may leave private orphans."""
    if "cris_sme_report.json" not in prepared.files or any(name not in REPORT_FILES for name in prepared.files):
        raise ValueError("Only recognized report exports can be published")
    if digest(prepared.files["cris_sme_report.json"]) != prepared.source_sha256:
        raise ValueError("Prepared source changed before publication")
    if len(prepared.files) > 64 or sum(map(len, prepared.files.values())) > 128 * 1024 * 1024:
        raise ValueError("Historical export bundle exceeds import limits")
    storage = storage or LocalStorage(artifact_root)
    with store.engine.begin() as c:
        store._access(c, tenant, principal, ADMIN, lock=True)
        existing = c.execute(select(s.historical_imports).where(s.historical_imports.c.tenant_id == tenant,
            or_(s.historical_imports.c.source_run_id == prepared.source_run_id,
                s.historical_imports.c.source_sha256 == prepared.source_sha256))).mappings().first()
        if existing:
            if existing["source_sha256"] != prepared.source_sha256 or existing["bundle_sha256"] != prepared.bundle_sha256:
                raise Rejected("Historical source run or export bundle changed; existing import retained", 409)
            for row in c.execute(select(s.artifacts).where(s.artifacts.c.tenant_id == tenant,
                                s.artifacts.c.job_id == existing["job_id"])).mappings():
                content = storage.read(row["key"], max_bytes=MAX_ARTIFACT_BYTES)
                if digest(content) != row["sha256"] or len(content) != row["size"]:
                    raise Rejected("Existing imported artifact failed integrity verification", 409)
            return {"job_id": existing["job_id"], "created": False}
        job, connection, now = new_id(), new_id(), store._now(c)
        artifact_root = artifact_root.resolve()
        artifact_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory = artifact_root / tenant
        directory.mkdir(exist_ok=True, mode=0o700)
        directory = directory / job
        directory.mkdir(mode=0o700)
        preview = prepared.preview()
        manifest = {**preview, "tenant_id": tenant, "job_id": job, "imported_at": now,
                    "origin": "historical_import", "collector_executed": False}
        files = {**prepared.files, "historical_import_manifest.json": (json.dumps(manifest, indent=2) + "\n").encode()}
        records = []
        for name, content in sorted(files.items()):
            path = directory / name
            with path.open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            path.chmod(0o600)
            storage.publish(str(path.relative_to(artifact_root)), content)
            records.append(dict(id=new_id(), tenant_id=tenant, job_id=job, name=name,
                                key=str(path.relative_to(artifact_root)), sha256=digest(content), size=len(content)))
        c.execute(insert(s.connections).values(id=connection, tenant_id=tenant,
            name=f"Historical {prepared.provider.upper()} / {prepared.source_run_id}"[:200], provider=prepared.provider,
            scope_id=prepared.scope_id, config=json.dumps({"origin": "historical_import"}),
            secret=store.cipher.encrypt(b"{}").decode(), enabled=False, verified_until=0))
        c.execute(insert(s.jobs).values(id=job, tenant_id=tenant, connection_id=connection,
            idempotency_key="historical:" + prepared.source_sha256, requested_by_issuer=principal.issuer,
            requested_by_subject=principal.subject, status="completed", requested_at=prepared.epoch, attempt=0,
            lease_token="", lease_until=0, cancel_requested=False, error_code=""))
        c.execute(insert(s.historical_imports).values(tenant_id=tenant, job_id=job, source_run_id=prepared.source_run_id,
            source_organization_id=prepared.source_organization_id, source_sha256=prepared.source_sha256,
            bundle_sha256=prepared.bundle_sha256, generated_at=prepared.generated_at, imported_at=now,
            provider=prepared.provider, scope_id=prepared.scope_id, reported_source_type=prepared.reported_source_type))
        c.execute(insert(s.artifacts), records)
        store._audit(c, tenant, principal.subject, "assessment.imported", job)
        return {"job_id": job, "created": True}
