# Confidence calibration utilities for making CRIS-SME scoring more empirically defensible.
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

from cris_sme.models.finding import Finding


DEFAULT_CONFIDENCE_CALIBRATION_PATH = Path("data/confidence_calibration.json")


class ConfidenceCalibrationEntry(BaseModel):
    """Empirical or review-backed confidence metadata for a CRIS-SME control."""

    control_id: str = Field(..., min_length=3)
    calibration_status: str = Field(..., min_length=3)
    validation_method: str = Field(..., min_length=3)
    benchmark_source: str = Field(..., min_length=3)
    empirical_agreement_rate: float = Field(..., ge=0.0, le=1.0)
    sample_size: int = Field(..., ge=0)
    notes: str = Field(..., min_length=8)


class ConfidenceCalibrationResult(BaseModel):
    """Calibrated confidence output for a single finding."""

    observed_confidence: float = Field(..., ge=0.0, le=1.0)
    calibrated_confidence: float = Field(..., ge=0.0, le=1.0)
    calibration_status: str = Field(..., min_length=3)
    validation_method: str = Field(..., min_length=3)
    benchmark_source: str = Field(..., min_length=3)
    empirical_agreement_rate: float = Field(..., ge=0.0, le=1.0)
    sample_size: int = Field(..., ge=0)
    empirical_weight: float = Field(..., ge=0.0, le=1.0)
    notes: str = Field(..., min_length=8)


@lru_cache(maxsize=1)
def load_confidence_calibration_catalog(
    path: str | Path = DEFAULT_CONFIDENCE_CALIBRATION_PATH,
) -> dict[str, ConfidenceCalibrationEntry]:
    """Load per-control confidence calibration metadata."""
    calibration_path = Path(path)
    raw_entries = json.loads(calibration_path.read_text(encoding="utf-8"))
    entries = [
        ConfidenceCalibrationEntry.model_validate(item)
        for item in raw_entries
    ]
    return {entry.control_id: entry for entry in entries}


def calibrate_finding_confidence(finding: Finding) -> ConfidenceCalibrationResult:
    """Blend observed confidence with empirical agreement metadata where available."""
    entry = load_confidence_calibration_catalog().get(finding.control_id)
    observed_confidence = float(finding.confidence)

    if entry is None:
        return ConfidenceCalibrationResult(
            observed_confidence=observed_confidence,
            calibrated_confidence=observed_confidence,
            calibration_status="unmapped",
            validation_method="no_catalog_entry",
            benchmark_source="none",
            empirical_agreement_rate=observed_confidence,
            sample_size=0,
            empirical_weight=0.0,
            notes="No confidence calibration metadata is currently recorded for this control.",
        )

    empirical_weight = _empirical_weight_for_status(entry.calibration_status)
    calibrated_confidence = round(
        (observed_confidence * (1.0 - empirical_weight))
        + (entry.empirical_agreement_rate * empirical_weight),
        4,
    )

    return ConfidenceCalibrationResult(
        observed_confidence=observed_confidence,
        calibrated_confidence=calibrated_confidence,
        calibration_status=entry.calibration_status,
        validation_method=entry.validation_method,
        benchmark_source=entry.benchmark_source,
        empirical_agreement_rate=entry.empirical_agreement_rate,
        sample_size=entry.sample_size,
        empirical_weight=empirical_weight,
        notes=entry.notes,
    )


def summarize_confidence_calibration(
    scored_findings: list[object],
) -> dict[str, object]:
    """Build a concise confidence-calibration summary for the report layer."""
    calibration_items = []
    for item in scored_findings:
        breakdown = getattr(item, "breakdown", None)
        finding = getattr(item, "finding", None)
        if breakdown is None or finding is None:
            continue
        calibration_items.append(
            {
                "control_id": getattr(finding, "control_id", ""),
                "calibration_status": getattr(breakdown, "calibration_status", "unknown"),
                "observed_confidence": getattr(breakdown, "observed_confidence", 0.0),
                "calibrated_confidence": getattr(breakdown, "calibrated_confidence", 0.0),
            }
        )

    if not calibration_items:
        return {
            "controls_with_calibration": 0,
            "average_observed_confidence": 0.0,
            "average_calibrated_confidence": 0.0,
            "status_counts": {},
        }

    status_counts: dict[str, int] = {}
    observed_total = 0.0
    calibrated_total = 0.0
    for item in calibration_items:
        status = str(item["calibration_status"])
        status_counts[status] = status_counts.get(status, 0) + 1
        observed_total += float(item["observed_confidence"])
        calibrated_total += float(item["calibrated_confidence"])

    count = len(calibration_items)
    return {
        "controls_with_calibration": count,
        "average_observed_confidence": round(observed_total / count, 4),
        "average_calibrated_confidence": round(calibrated_total / count, 4),
        "status_counts": status_counts,
        "method_summary": (
            "Observed per-control confidence is blended with a lightweight empirical agreement profile "
            "derived from live Azure validation, synthetic regression testing, and documented review."
        ),
    }


def _empirical_weight_for_status(status: str) -> float:
    """Choose how strongly empirical agreement should influence the final confidence."""
    normalized = status.strip().lower()
    if normalized == "validated":
        return 0.5
    if normalized == "provisional":
        return 0.3
    return 0.0
