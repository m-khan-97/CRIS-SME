# Central control catalog for stable CRIS-SME control metadata and remediation guidance.
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

from cris_sme.models.finding import FindingCategory, RemediationCostTier


DEFAULT_CONTROL_CATALOG_PATH = Path("data/control_catalog.json")


class ControlCatalogEntry(BaseModel):
    """Stable metadata describing a CRIS-SME control definition."""

    control_id: str = Field(..., min_length=3)
    category: FindingCategory
    title: str = Field(..., min_length=5)
    mapping: list[str] = Field(default_factory=list)
    remediation_summary: str = Field(..., min_length=8)
    remediation_cost_tier: RemediationCostTier


@lru_cache(maxsize=1)
def load_control_catalog(
    path: str | Path = DEFAULT_CONTROL_CATALOG_PATH,
) -> dict[str, ControlCatalogEntry]:
    """Load the central control catalog as a control-id keyed mapping."""
    catalog_path = Path(path)
    raw_entries = json.loads(catalog_path.read_text(encoding="utf-8"))
    entries = [ControlCatalogEntry.model_validate(item) for item in raw_entries]
    return {entry.control_id: entry for entry in entries}


def get_control_entry(control_id: str) -> ControlCatalogEntry:
    """Return a control catalog entry or raise a descriptive error."""
    entry = load_control_catalog().get(control_id)
    if entry is None:
        raise KeyError(f"Control '{control_id}' is missing from the central control catalog.")
    return entry
