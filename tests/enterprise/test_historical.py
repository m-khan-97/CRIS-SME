from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

import pytest
from sqlalchemy import delete, insert, select

from cris_sme.enterprise import schema as s
from cris_sme.enterprise.auth import Principal
from cris_sme.enterprise.historical import prepare_import, publish_import
from cris_sme.enterprise.store import Rejected
from tests.enterprise.conftest import ISSUER


def source_report():
    return {"report_schema_version": "2.0.0", "generated_at": "2026-07-03T12:40:13.123456Z", "collector_mode": "aws",
        "organizations": [{"organization_id": "legacy-org", "organization_name": "Original display name", "provider": "aws",
            "tenant_scope": "123456789012", "collection_details": {"dataset_source_type": "vulnerable_lab"}}],
        "run_metadata": {"run_id": "original-run", "generated_at": "2026-07-03T12:40:13.123456Z", "providers_in_scope": ["aws"]},
        "prioritized_risks": [{"finding_id": "original-finding", "organization_id": "legacy-org"}],
        "resource_context": {}, "assessment_runner": {}}


def source(tmp_path, payload=None, *, exports=False, history=False):
    root = tmp_path / "source"
    root.mkdir(exist_ok=True)
    name = "cris_sme_report_20260703T124013Z.json" if history else "cris_sme_report.json"
    payload = payload or source_report()
    if exports:
        payload["report_artifacts"] = {"json_report": str(root / name), "html_report": str(root / "cris_sme_report.html")}
        (root / "cris_sme_report.html").write_bytes(b"<html>Original export</html>")
    raw = (json.dumps(payload, indent=3) + "\n").encode()
    (root / name).write_bytes(raw)
    return root, Path(name), raw


def test_preparation_preserves_bytes_and_does_not_write_artifacts(tmp_path):
    root, name, raw = source(tmp_path)
    before = set(root.iterdir())
    prepared = prepare_import(root, name)
    assert set(root.iterdir()) == before
    assert prepared.files == {"cris_sme_report.json": raw}
    assert prepared.source_sha256 == hashlib.sha256(raw).hexdigest()
    assert prepared.reported_source_type == "vulnerable_lab"
    assert prepared.generated_at.endswith("123456Z")


@pytest.mark.parametrize("field,value", [
    ("organizations", []), ("organizations", [{}, {}]), ("collector_mode", "azure"),
    ("generated_at", "2026-07-03T12:40:13"), ("generated_at", "9999-01-01T00:00:00Z"),
    ("resource_context", None), ("assessment_runner", None), ("prioritized_risks", {}),
    ("run_metadata", {"run_id": "bad/run", "providers_in_scope": ["aws"]}),
    ("run_metadata", {"run_id": "original-run", "providers_in_scope": ["azure"]}),
])
def test_invalid_report_scope_and_shape_rejected(tmp_path, field, value):
    payload = source_report()
    payload[field] = value
    root, name, _ = source(tmp_path, payload)
    with pytest.raises(ValueError):
        prepare_import(root, name)


def test_missing_source_identity_and_conflicting_time_rejected(tmp_path):
    payload = source_report()
    payload["organizations"][0]["organization_id"] = ""
    root, name, _ = source(tmp_path, payload)
    with pytest.raises(ValueError):
        prepare_import(root, name)
    payload = source_report()
    payload["run_metadata"]["generated_at"] = "2026-07-04T12:00:00Z"
    (root / name).write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="Conflicting"):
        prepare_import(root, name)


def test_duplicate_json_and_nonfinite_values_rejected(tmp_path):
    root, name, raw = source(tmp_path)
    for content in (b'{"collector_mode":"aws",' + raw[1:], raw.replace(b'"resource_context": {}', b'"resource_context": NaN')):
        (root / name).write_bytes(content)
        with pytest.raises(ValueError):
            prepare_import(root, name)


def test_symlink_and_parent_escape_rejected(tmp_path):
    root, name, _ = source(tmp_path)
    link = root / "link"
    link.mkdir()
    (link / name).symlink_to(root / name)
    with pytest.raises(OSError):
        prepare_import(root, Path("link") / name)
    with pytest.raises(ValueError):
        prepare_import(root, Path("../source") / name)


def test_export_inventory_is_anchored_and_history_never_borrows_current_exports(tmp_path):
    root, name, _ = source(tmp_path, exports=True)
    prepared = prepare_import(root, name, include_exports=True)
    assert prepared.files["cris_sme_report.html"] == b"<html>Original export</html>"
    history = Path("cris_sme_report_20260703T124013Z.json")
    (root / history).write_bytes((root / name).read_bytes())
    assert set(prepare_import(root, history, include_exports=True).files) == {"cris_sme_report.json"}
    (root / "cris_sme_report.html").unlink()
    assert prepare_import(root, name, include_exports=True).skipped_exports == ("cris_sme_report.html",)


def test_export_symlinks_rejected(tmp_path):
    root, name, _ = source(tmp_path, exports=True)
    (root / "cris_sme_report.html").unlink()
    (root / "cris_sme_report.html").symlink_to(root / name)
    with pytest.raises(OSError):
        prepare_import(root, name, include_exports=True)


def test_export_inventory_cannot_claim_another_report(tmp_path):
    root, name, _ = source(tmp_path, exports=True)
    payload = json.loads((root / name).read_text())
    payload["report_artifacts"]["json_report"] = str(root / "other.json")
    (root / name).write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="different source"):
        prepare_import(root, name, include_exports=True)


def test_import_is_private_idempotent_and_never_a_live_connection(context, tmp_path):
    ctx = context
    root, name, raw = source(tmp_path, exports=True)
    prepared = prepare_import(root, name, include_exports=True)
    result = publish_import(ctx["store"], ctx["tenant"], ctx["principal"], prepared, ctx["root"])
    repeat = publish_import(ctx["store"], ctx["tenant"], ctx["principal"], prepared, ctx["root"])
    assert result["created"] is True and repeat == {"job_id": result["job_id"], "created": False}
    url = f"/api/v1/tenants/{ctx['tenant']}"
    job = ctx["client"].get(url + "/assessments/" + result["job_id"]).json()
    assert job["origin"] == "historical_import" and job["status"] == "completed" and job["attempt"] == 0
    assert job["historical_import"]["source_run_id"] == "original-run"
    assert job["historical_import"]["reported_source_type"] == "vulnerable_lab"
    assert ctx["client"].get(url + "/assessments").json()["assessments"][0]["historical_import"] == job["historical_import"]
    artifact = next(a for a in job["artifacts"] if a["name"] == "cris_sme_report.json")
    assert ctx["client"].get(url + "/artifacts/" + artifact["id"]).content == raw
    assert (root / name).read_bytes() == raw
    assert ctx["store"].claim() is None
    connection = ctx["client"].get(url + "/connections").json()["connections"][0]
    assert connection["origin"] == "historical_archive" and not connection["enabled"]
    assert ctx["client"].post(url + f"/connections/{connection['id']}/verify").status_code == 409
    assert ctx["client"].post(url + "/assessments", headers={"Idempotency-Key": "not-live"},
        json={"connection_id": connection["id"], "authorization_confirmed": True}).status_code == 409
    assert "assessment.imported" in [event["action"] for event in ctx["store"].audit_list(ctx["tenant"], ctx["principal"])]


def test_changed_source_or_exports_cannot_overwrite_import(context, tmp_path):
    ctx = context
    root, name, raw = source(tmp_path, exports=True)
    original = prepare_import(root, name, include_exports=True)
    job = publish_import(ctx["store"], ctx["tenant"], ctx["principal"], original, ctx["root"])
    (root / "cris_sme_report.html").write_bytes(b"changed export")
    with pytest.raises(Rejected, match="changed"):
        publish_import(ctx["store"], ctx["tenant"], ctx["principal"], prepare_import(root, name, include_exports=True), ctx["root"])
    payload = json.loads(raw)
    payload["prioritized_risks"] = []
    (root / name).write_text(json.dumps(payload))
    with pytest.raises(Rejected, match="changed"):
        publish_import(ctx["store"], ctx["tenant"], ctx["principal"], prepare_import(root, name), ctx["root"])
    assert ctx["store"].job_list(ctx["tenant"], ctx["principal"])[0]["id"] == job["job_id"]


@pytest.mark.parametrize("role", ["operator", "analyst", "auditor"])
def test_import_requires_administrative_membership(context, tmp_path, role):
    ctx = context
    ctx["store"].member(ctx["tenant"], ctx["principal"], "reader", role)
    root, name, _ = source(tmp_path)
    with pytest.raises(Rejected) as error:
        publish_import(ctx["store"], ctx["tenant"], Principal(ISSUER, "reader"), prepare_import(root, name), ctx["root"])
    assert error.value.status == 403
    assert not ctx["store"].job_list(ctx["tenant"], ctx["principal"])


def test_foreign_membership_cannot_import_or_read(context, tmp_path, token):
    ctx = context
    other = ctx["store"].bootstrap(Principal(ISSUER, "other"), "Same display name")
    root, name, _ = source(tmp_path)
    prepared = prepare_import(root, name)
    with pytest.raises(Rejected):
        publish_import(ctx["store"], other, ctx["principal"], prepared, ctx["root"])
    job = publish_import(ctx["store"], ctx["tenant"], ctx["principal"], prepared, ctx["root"])
    ctx["client"].headers["Authorization"] = "Bearer " + token("other")
    assert ctx["client"].get(f"/api/v1/tenants/{ctx['tenant']}/assessments/{job['job_id']}").status_code == 404


def test_concurrent_imports_deduplicate(context, tmp_path):
    ctx = context
    root, name, _ = source(tmp_path)
    prepared = prepare_import(root, name)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: publish_import(ctx["store"], ctx["tenant"], ctx["principal"], prepared, ctx["root"]), range(2)))
    assert len({item["job_id"] for item in results}) == 1
    assert sum(item["created"] for item in results) == 1


def test_registration_failure_rolls_back_metadata_without_touching_source(context, tmp_path, monkeypatch):
    ctx = context
    root, name, raw = source(tmp_path)
    def unavailable(*args):
        raise RuntimeError("Audit unavailable")
    monkeypatch.setattr(ctx["store"], "_audit", unavailable)
    with pytest.raises(RuntimeError):
        publish_import(ctx["store"], ctx["tenant"], ctx["principal"], prepare_import(root, name), ctx["root"])
    assert ctx["store"].job_list(ctx["tenant"], ctx["principal"]) == []
    assert ctx["store"].connection_list(ctx["tenant"], ctx["principal"]) == []
    assert (root / name).read_bytes() == raw


def test_v1_upgrade_preserves_existing_tenants_and_is_idempotent(store):
    owner = Principal(ISSUER, "owner")
    tenant = store.bootstrap(owner, "Existing tenant")
    with store.engine.begin() as c:
        s.historical_imports.drop(c)
        c.execute(delete(s.versions))
        c.execute(insert(s.versions).values(version=1))
    s.migrate(store.engine)
    s.migrate(store.engine)
    store.check_schema()
    assert store.tenants(owner)[0]["id"] == tenant
    with store.engine.connect() as c:
        assert list(c.execute(select(s.historical_imports)).mappings()) == []


def test_unknown_schema_version_is_not_migrated(store):
    with store.engine.begin() as c:
        c.execute(delete(s.versions))
        c.execute(insert(s.versions).values(version=99))
    with pytest.raises(RuntimeError, match="Unsupported"):
        s.migrate(store.engine)
