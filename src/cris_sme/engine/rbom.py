# Risk Bill of Materials generation for CRIS-SME assessment integrity.
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cris_sme.models.platform import (
    RiskBillOfMaterials,
    RiskBillOfMaterialsArtifact,
    RiskBillOfMaterialsSignature,
    RiskBillOfMaterialsVerificationResult,
)


SCORING_MODEL_ID = "cris_sme_deterministic_scoring_v2"


def build_risk_bill_of_materials(
    report: dict[str, Any],
    *,
    artifact_paths: dict[str, str | Path] | None = None,
) -> RiskBillOfMaterials:
    """Build a deterministic integrity/provenance manifest for an assessment."""
    run_metadata = report.get("run_metadata", {})
    if not isinstance(run_metadata, dict):
        run_metadata = {}
    policy_pack = run_metadata.get("policy_pack", {})
    if not isinstance(policy_pack, dict):
        policy_pack = {}

    prioritized = report.get("prioritized_risks", [])
    if not isinstance(prioritized, list):
        prioritized = []

    return RiskBillOfMaterials(
        generated_at=str(report.get("generated_at") or "1970-01-01T00:00:00Z"),
        run_id=str(run_metadata.get("run_id") or "run_unknown"),
        report_schema_version=str(report.get("report_schema_version", "unknown")),
        engine_version=str(run_metadata.get("engine_version", "unknown")),
        scoring_model=SCORING_MODEL_ID,
        policy_pack_version=str(policy_pack.get("policy_pack_version", "unknown")),
        collector_mode=str(report.get("collector_mode", "unknown")),
        providers_in_scope=[
            str(provider)
            for provider in run_metadata.get("providers_in_scope", [])
            if str(provider).strip()
        ],
        canonical_report_sha256=canonical_report_sha256(report),
        control_ids=_control_ids(prioritized),
        finding_ids=_finding_ids(prioritized),
        evidence_refs=_evidence_refs(prioritized),
        evidence_sufficiency_counts=_evidence_sufficiency_counts(prioritized),
        decision_ledger_event_counts=_decision_ledger_event_counts(report),
        artifacts=_artifact_hashes(artifact_paths or {}),
        signature_note=(
            "This RBOM is an integrity manifest using deterministic SHA-256 hashes. "
            "It is not a public-key cryptographic signature until an external signing "
            "key or certificate workflow is attached."
        ),
    )


def write_risk_bill_of_materials(
    rbom: RiskBillOfMaterials,
    output_path: str | Path,
) -> Path:
    """Write a Risk Bill of Materials JSON artifact."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rbom.model_dump(mode="json"), indent=2), encoding="utf-8")
    return path


def sign_risk_bill_of_materials(
    rbom: RiskBillOfMaterials | dict[str, Any],
    *,
    signing_key: str,
    key_id: str = "local",
    signed_at: str | None = None,
) -> RiskBillOfMaterialsSignature:
    """Create a detached HMAC-SHA256 signature for an RBOM."""
    rbom_payload = _canonical_rbom_payload(rbom)
    signature = hmac.new(
        signing_key.encode("utf-8"),
        rbom_payload,
        hashlib.sha256,
    ).hexdigest()
    return RiskBillOfMaterialsSignature(
        signed_at=signed_at or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        key_id=key_id,
        rbom_sha256=hashlib.sha256(rbom_payload).hexdigest(),
        signature=signature,
        signature_note=(
            "Detached HMAC-SHA256 signature over the canonical RBOM payload. "
            "This provides shared-secret integrity/authenticity and can later be "
            "replaced or complemented by public-key signing."
        ),
    )


def write_risk_bill_of_materials_signature(
    signature: RiskBillOfMaterialsSignature,
    output_path: str | Path,
) -> Path:
    """Write a detached RBOM signature JSON artifact."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(signature.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    return path


def verify_risk_bill_of_materials(
    *,
    report_path: str | Path,
    rbom_path: str | Path | None = None,
    signature_path: str | Path | None = None,
    signing_key: str | None = None,
    base_dir: str | Path | None = None,
) -> RiskBillOfMaterialsVerificationResult:
    """Verify report and artifact hashes against a CRIS-SME RBOM."""
    report_file = Path(report_path)
    root = Path(base_dir) if base_dir is not None else Path.cwd()
    errors: list[str] = []

    if not report_file.exists():
        return RiskBillOfMaterialsVerificationResult(
            verified=False,
            report_hash_verified=False,
            artifact_hashes_verified=False,
            signature_verified=False if signature_path or signing_key else None,
            checked_artifact_count=0,
            errors=[f"Report file not found: {report_file}"],
        )

    try:
        report = json.loads(report_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return RiskBillOfMaterialsVerificationResult(
            verified=False,
            report_hash_verified=False,
            artifact_hashes_verified=False,
            signature_verified=False if signature_path or signing_key else None,
            checked_artifact_count=0,
            errors=[f"Report JSON is invalid: {exc}"],
        )

    rbom_raw = _load_rbom(report=report, rbom_path=rbom_path)
    if rbom_raw is None:
        return RiskBillOfMaterialsVerificationResult(
            verified=False,
            report_hash_verified=False,
            artifact_hashes_verified=False,
            signature_verified=False if signature_path or signing_key else None,
            checked_artifact_count=0,
            errors=["RBOM not found in report and no valid RBOM path was supplied."],
        )

    try:
        rbom = RiskBillOfMaterials.model_validate(rbom_raw)
    except Exception as exc:
        return RiskBillOfMaterialsVerificationResult(
            verified=False,
            report_hash_verified=False,
            artifact_hashes_verified=False,
            signature_verified=False if signature_path or signing_key else None,
            checked_artifact_count=0,
            errors=[f"RBOM schema validation failed: {exc}"],
        )

    actual_report_hash = canonical_report_sha256(report)
    report_hash_verified = actual_report_hash == rbom.canonical_report_sha256
    if not report_hash_verified:
        errors.append(
            "Canonical report hash mismatch: "
            f"expected {rbom.canonical_report_sha256}, got {actual_report_hash}"
        )

    missing_artifacts: list[str] = []
    mismatched_artifacts: list[str] = []
    checked_artifact_count = 0
    for artifact in rbom.artifacts:
        artifact_path = _resolve_artifact_path(artifact.path, root)
        if not artifact_path.exists() or not artifact_path.is_file():
            missing_artifacts.append(artifact.artifact_name)
            continue
        checked_artifact_count += 1
        actual_hash = _file_sha256(artifact_path)
        if actual_hash != artifact.sha256:
            mismatched_artifacts.append(artifact.artifact_name)

    artifact_hashes_verified = not missing_artifacts and not mismatched_artifacts
    signature_verified: bool | None = None
    signature_algorithm: str | None = None
    signature_key_id: str | None = None
    if signature_path is not None or signing_key is not None:
        signature_result = _verify_rbom_signature(
            rbom=rbom,
            signature_path=signature_path,
            signing_key=signing_key,
        )
        signature_verified = signature_result["verified"]
        signature_algorithm = signature_result.get("algorithm")
        signature_key_id = signature_result.get("key_id")
        errors.extend(signature_result["errors"])

    verified = (
        report_hash_verified
        and artifact_hashes_verified
        and (signature_verified is not False)
        and not errors
    )
    return RiskBillOfMaterialsVerificationResult(
        verified=verified,
        report_hash_verified=report_hash_verified,
        artifact_hashes_verified=artifact_hashes_verified,
        signature_verified=signature_verified,
        signature_algorithm=signature_algorithm,
        signature_key_id=signature_key_id,
        checked_artifact_count=checked_artifact_count,
        missing_artifacts=missing_artifacts,
        mismatched_artifacts=mismatched_artifacts,
        errors=errors,
    )


def canonical_report_sha256(report: dict[str, Any]) -> str:
    """Hash the report in canonical form while excluding the RBOM itself."""
    canonical_report = _without_rbom(report)
    payload = json.dumps(
        canonical_report,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def canonical_rbom_sha256(rbom: RiskBillOfMaterials | dict[str, Any]) -> str:
    """Return the canonical SHA-256 hash of an RBOM payload."""
    return hashlib.sha256(_canonical_rbom_payload(rbom)).hexdigest()


def _load_rbom(
    *,
    report: dict[str, Any],
    rbom_path: str | Path | None,
) -> dict[str, Any] | None:
    if rbom_path is not None:
        path = Path(rbom_path)
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return None
            return raw if isinstance(raw, dict) else None

    embedded = report.get("risk_bill_of_materials")
    return embedded if isinstance(embedded, dict) else None


def _verify_rbom_signature(
    *,
    rbom: RiskBillOfMaterials,
    signature_path: str | Path | None,
    signing_key: str | None,
) -> dict[str, Any]:
    errors: list[str] = []
    if signing_key is None:
        return {
            "verified": False,
            "algorithm": None,
            "key_id": None,
            "errors": ["Signing key is required when signature verification is requested."],
        }
    if signature_path is None:
        return {
            "verified": False,
            "algorithm": None,
            "key_id": None,
            "errors": ["Signature path is required when signature verification is requested."],
        }

    path = Path(signature_path)
    if not path.exists():
        return {
            "verified": False,
            "algorithm": None,
            "key_id": None,
            "errors": [f"Signature file not found: {path}"],
        }

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        signature = RiskBillOfMaterialsSignature.model_validate(raw)
    except Exception as exc:
        return {
            "verified": False,
            "algorithm": None,
            "key_id": None,
            "errors": [f"RBOM signature validation failed: {exc}"],
        }

    if signature.algorithm != "hmac-sha256":
        errors.append(f"Unsupported RBOM signature algorithm: {signature.algorithm}")

    rbom_payload = _canonical_rbom_payload(rbom)
    actual_rbom_hash = hashlib.sha256(rbom_payload).hexdigest()
    if actual_rbom_hash != signature.rbom_sha256:
        errors.append(
            "RBOM payload hash mismatch: "
            f"expected {signature.rbom_sha256}, got {actual_rbom_hash}"
        )

    expected_signature = hmac.new(
        signing_key.encode("utf-8"),
        rbom_payload,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_signature, signature.signature):
        errors.append("RBOM signature mismatch.")

    return {
        "verified": not errors,
        "algorithm": signature.algorithm,
        "key_id": signature.key_id,
        "errors": errors,
    }


def _canonical_rbom_payload(rbom: RiskBillOfMaterials | dict[str, Any]) -> bytes:
    if isinstance(rbom, RiskBillOfMaterials):
        raw = rbom.model_dump(mode="json")
    else:
        raw = dict(rbom)
    return json.dumps(
        raw,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def _without_rbom(report: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the report excluding self-referential RBOM fields."""
    cleaned = dict(report)
    cleaned.pop("risk_bill_of_materials", None)
    report_artifacts = cleaned.get("report_artifacts")
    if isinstance(report_artifacts, dict):
        artifacts = dict(report_artifacts)
        artifacts.pop("risk_bill_of_materials", None)
        cleaned["report_artifacts"] = artifacts
    return cleaned


def _control_ids(prioritized: list[object]) -> list[str]:
    return sorted(
        {
            str(item.get("control_id"))
            for item in prioritized
            if isinstance(item, dict) and item.get("control_id")
        }
    )


def _finding_ids(prioritized: list[object]) -> list[str]:
    return sorted(
        {
            str(item.get("finding_id"))
            for item in prioritized
            if isinstance(item, dict) and item.get("finding_id")
        }
    )


def _evidence_refs(prioritized: list[object]) -> list[str]:
    refs: set[str] = set()
    for item in prioritized:
        if not isinstance(item, dict):
            continue
        trace = item.get("finding_trace", {})
        if not isinstance(trace, dict):
            continue
        evidence_refs = trace.get("evidence_refs", [])
        if not isinstance(evidence_refs, list):
            continue
        refs.update(str(ref) for ref in evidence_refs if str(ref).strip())
    return sorted(refs)


def _evidence_sufficiency_counts(prioritized: list[object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in prioritized:
        if not isinstance(item, dict):
            continue
        quality = item.get("evidence_quality", {})
        if not isinstance(quality, dict):
            continue
        sufficiency = str(quality.get("sufficiency", "unknown"))
        counts[sufficiency] = counts.get(sufficiency, 0) + 1
    return counts


def _decision_ledger_event_counts(report: dict[str, Any]) -> dict[str, int]:
    ledger = report.get("decision_ledger", {})
    if not isinstance(ledger, dict):
        return {}
    events = ledger.get("events", [])
    if not isinstance(events, list):
        return {}

    counts: dict[str, int] = {}
    for event in events:
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("event_type", "unknown"))
        counts[event_type] = counts.get(event_type, 0) + 1
    return counts


def _artifact_hashes(
    artifact_paths: dict[str, str | Path],
) -> list[RiskBillOfMaterialsArtifact]:
    artifacts: list[RiskBillOfMaterialsArtifact] = []
    for artifact_name, raw_path in sorted(artifact_paths.items()):
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            continue
        artifacts.append(
            RiskBillOfMaterialsArtifact(
                artifact_name=artifact_name,
                path=str(path),
                sha256=_file_sha256(path),
                size_bytes=path.stat().st_size,
            )
        )
    return artifacts


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_artifact_path(path: str, base_dir: Path) -> Path:
    artifact_path = Path(path)
    if artifact_path.is_absolute():
        return artifact_path
    return base_dir / artifact_path
