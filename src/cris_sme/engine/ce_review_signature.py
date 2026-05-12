# Integrity metadata and optional signatures for CE human-review ledgers.
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


CE_REVIEW_LEDGER_SCHEMA_VERSION = "0.1.0"
CE_REVIEW_SIGNATURE_ALGORITHM = "hmac-sha256"
CE_REVIEW_HASH_ALGORITHM = "sha256"

_DECISION_FIELDS = (
    "state",
    "final_answer",
    "final_status",
    "reviewer",
    "reviewed_at",
    "reviewer_note",
    "override_reason",
    "additional_evidence_reference",
)


def build_signed_ce_review_ledger(
    *,
    answer_pack: dict[str, Any],
    review_decisions: dict[str, dict[str, Any]],
    reviewer: dict[str, Any] | None = None,
    generated_at: str | None = None,
    signing_key: str | None = None,
    key_id: str = "local",
) -> dict[str, Any]:
    """Build a human-review ledger with deterministic hashes and optional HMAC."""
    body = _ledger_body(
        answer_pack=answer_pack,
        review_decisions=review_decisions,
        reviewer=reviewer,
        generated_at=generated_at,
    )
    body_hash = canonical_sha256(body)
    decisions = body["review_decisions"]
    integrity = {
        "hash_algorithm": CE_REVIEW_HASH_ALGORITHM,
        "canonical_ledger_sha256": body_hash,
        "canonical_decisions_sha256": canonical_sha256(decisions),
        "source_answer_pack_sha256": canonical_sha256(answer_pack),
        "reviewed_decision_count": len(decisions),
        "signature_boundary": (
            "This ledger signs reviewer decisions and source-pack binding only. "
            "It does not certify Cyber Essentials compliance and does not alter "
            "CRIS-SME deterministic risk scores."
        ),
    }
    ledger = {**body, "integrity": integrity}
    if signing_key:
        ledger["signature"] = sign_ce_review_ledger_body(
            body,
            signing_key=signing_key,
            key_id=key_id,
        )
    return ledger


def write_signed_ce_review_ledger(ledger: dict[str, Any], output_path: str | Path) -> Path:
    """Write a signed or hash-bound CE review ledger."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=2, sort_keys=True), encoding="utf-8")
    return path


def verify_ce_review_ledger(
    ledger: dict[str, Any] | str | Path,
    *,
    answer_pack: dict[str, Any] | None = None,
    signing_key: str | None = None,
) -> dict[str, Any]:
    """Verify CE review-ledger hashes and optional HMAC signature."""
    raw = _load_ledger(ledger)
    errors: list[str] = []
    body = _body_from_ledger(raw)
    integrity = raw.get("integrity") if isinstance(raw.get("integrity"), dict) else {}
    signature = raw.get("signature") if isinstance(raw.get("signature"), dict) else None

    expected_body_hash = _clean(integrity.get("canonical_ledger_sha256"))
    actual_body_hash = canonical_sha256(body)
    ledger_hash_verified = bool(expected_body_hash) and hmac.compare_digest(
        expected_body_hash,
        actual_body_hash,
    )
    if not ledger_hash_verified:
        errors.append(
            "Canonical ledger hash mismatch: "
            f"expected {expected_body_hash or '<missing>'}, got {actual_body_hash}"
        )

    decisions = body.get("review_decisions", [])
    expected_decisions_hash = _clean(integrity.get("canonical_decisions_sha256"))
    actual_decisions_hash = canonical_sha256(decisions)
    decisions_hash_verified = bool(expected_decisions_hash) and hmac.compare_digest(
        expected_decisions_hash,
        actual_decisions_hash,
    )
    if not decisions_hash_verified:
        errors.append(
            "Canonical decisions hash mismatch: "
            f"expected {expected_decisions_hash or '<missing>'}, got {actual_decisions_hash}"
        )

    answer_pack_hash_verified: bool | None = None
    if answer_pack is not None:
        expected_answer_pack_hash = _clean(integrity.get("source_answer_pack_sha256"))
        actual_answer_pack_hash = canonical_sha256(answer_pack)
        answer_pack_hash_verified = bool(expected_answer_pack_hash) and hmac.compare_digest(
            expected_answer_pack_hash,
            actual_answer_pack_hash,
        )
        if not answer_pack_hash_verified:
            errors.append(
                "Source answer-pack hash mismatch: "
                f"expected {expected_answer_pack_hash or '<missing>'}, got {actual_answer_pack_hash}"
            )

    signature_verified: bool | None = None
    if signature is not None or signing_key is not None:
        signature_verified = _verify_signature(
            body=body,
            signature=signature,
            signing_key=signing_key,
            errors=errors,
        )

    verified = (
        ledger_hash_verified
        and decisions_hash_verified
        and (answer_pack_hash_verified is not False)
        and (signature_verified is not False)
        and not errors
    )
    return {
        "verified": verified,
        "ledger_hash_verified": ledger_hash_verified,
        "decisions_hash_verified": decisions_hash_verified,
        "answer_pack_hash_verified": answer_pack_hash_verified,
        "signature_verified": signature_verified,
        "signature_algorithm": signature.get("algorithm") if signature else None,
        "signature_key_id": signature.get("key_id") if signature else None,
        "reviewed_decision_count": len(decisions) if isinstance(decisions, list) else 0,
        "errors": errors,
    }


def sign_ce_review_ledger_body(
    body: dict[str, Any],
    *,
    signing_key: str,
    key_id: str = "local",
    signed_at: str | None = None,
) -> dict[str, Any]:
    """Create a detached HMAC-SHA256 signature over a canonical ledger body."""
    payload = canonical_payload(body)
    signature = hmac.new(
        signing_key.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return {
        "signature_schema_version": CE_REVIEW_LEDGER_SCHEMA_VERSION,
        "algorithm": CE_REVIEW_SIGNATURE_ALGORITHM,
        "key_id": key_id,
        "signed_at": signed_at or _utc_now(),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "signature": signature,
        "signature_note": (
            "Detached HMAC-SHA256 signature over the canonical CE reviewer-ledger "
            "body. Use a managed signing secret in real assurance workflows."
        ),
    }


def canonical_sha256(payload: Any) -> str:
    """Return a deterministic SHA-256 hash for JSON-compatible content."""
    return hashlib.sha256(canonical_payload(payload)).hexdigest()


def canonical_payload(payload: Any) -> bytes:
    """Return canonical JSON bytes for hashing or signing."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def _ledger_body(
    *,
    answer_pack: dict[str, Any],
    review_decisions: dict[str, dict[str, Any]],
    reviewer: dict[str, Any] | None,
    generated_at: str | None,
) -> dict[str, Any]:
    question_set = answer_pack.get("question_set", {})
    if not isinstance(question_set, dict):
        question_set = {}
    return {
        "ledger_schema_version": CE_REVIEW_LEDGER_SCHEMA_VERSION,
        "ledger_type": "cris_sme_ce_human_review_ledger",
        "generated_at": generated_at or _utc_now(),
        "reviewer": _clean_reviewer(reviewer or {}),
        "source": {
            "answer_pack_name": answer_pack.get("pack_name", "unknown"),
            "answer_pack_schema_version": answer_pack.get("pack_schema_version", "unknown"),
            "mapping_schema_version": answer_pack.get("mapping_schema_version", "unknown"),
            "question_set": {
                "name": question_set.get("name", "unknown"),
                "version": question_set.get("version", "unknown"),
                "requirements_version": question_set.get("requirements_version", "unknown"),
                "effective_from": question_set.get("effective_from", "unknown"),
            },
            "policy_pack_version": _policy_pack_version(answer_pack),
        },
        "review_decisions": _normalise_decisions(review_decisions),
    }


def _body_from_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in ledger.items()
        if key not in {"integrity", "signature"}
    }


def _normalise_decisions(review_decisions: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for question_id in sorted(str(key) for key in review_decisions):
        decision = review_decisions.get(question_id, {})
        if not isinstance(decision, dict):
            decision = {}
        row = {"question_id": question_id}
        for field in _DECISION_FIELDS:
            row[field] = _clean(decision.get(field))
        rows.append(row)
    return rows


def _verify_signature(
    *,
    body: dict[str, Any],
    signature: dict[str, Any] | None,
    signing_key: str | None,
    errors: list[str],
) -> bool:
    signature_errors: list[str] = []
    if signing_key is None:
        errors.append("Signing key is required when signature verification is requested.")
        return False
    if signature is None:
        errors.append("Signature block is missing from the CE review ledger.")
        return False
    if signature.get("algorithm") != CE_REVIEW_SIGNATURE_ALGORITHM:
        signature_errors.append(f"Unsupported CE review signature algorithm: {signature.get('algorithm')}")

    payload = canonical_payload(body)
    actual_payload_hash = hashlib.sha256(payload).hexdigest()
    if signature.get("payload_sha256") != actual_payload_hash:
        signature_errors.append(
            "Signature payload hash mismatch: "
            f"expected {signature.get('payload_sha256')}, got {actual_payload_hash}"
        )

    expected_signature = hmac.new(
        signing_key.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_signature, str(signature.get("signature", ""))):
        signature_errors.append("CE review ledger signature mismatch.")
    errors.extend(signature_errors)
    return not signature_errors


def _load_ledger(ledger: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(ledger, dict):
        return ledger
    path = Path(ledger)
    return json.loads(path.read_text(encoding="utf-8"))


def _policy_pack_version(answer_pack: dict[str, Any]) -> str:
    for key in ("policy_pack_version", "policy_pack"):
        value = answer_pack.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            nested = value.get("policy_pack_version") or value.get("version")
            if nested:
                return str(nested)
    return "not_recorded_in_answer_pack"


def _clean_reviewer(reviewer: dict[str, Any]) -> dict[str, str]:
    return {
        "name": _clean(reviewer.get("name")),
        "role": _clean(reviewer.get("role")),
        "organisation": _clean(reviewer.get("organisation") or reviewer.get("organization")),
        "reviewer_id": _clean(reviewer.get("reviewer_id") or reviewer.get("id")),
    }


def _clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
