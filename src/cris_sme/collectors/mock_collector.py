# Mock collector that loads representative findings and synthetic posture data for MVP development.
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cris_sme.collectors.providers import get_profile_adapter
from cris_sme.models.cloud_profile import CloudProfile
from cris_sme.models.finding import Finding


class MockCollector:
    """Load validated mock inputs from the repository data directory."""

    def __init__(
        self,
        findings_path: str | Path | None = None,
        profiles_path: str | Path | None = None,
    ) -> None:
        self.findings_path = (
            Path(findings_path) if findings_path else Path("data/sample_findings.json")
        )
        self.profiles_path = (
            Path(profiles_path)
            if profiles_path
            else Path("data/synthetic_sme_profiles.json")
        )

    def collect_findings(self) -> list[Finding]:
        """Return validated sample findings from JSON."""
        raw_items = json.loads(self.findings_path.read_text(encoding="utf-8"))
        return [Finding.model_validate(item) for item in raw_items]

    def collect_raw_profiles(self) -> list[dict[str, Any]]:
        """Return raw provider records before provider-specific normalization."""
        return json.loads(self.profiles_path.read_text(encoding="utf-8"))

    def collect_profiles(self) -> list[CloudProfile]:
        """Return provider-normalized synthetic cloud posture profiles from JSON."""
        profiles: list[CloudProfile] = []

        for raw_item in self.collect_raw_profiles():
            provider = str(raw_item.get("provider", "azure"))
            adapter = get_profile_adapter(provider)
            profile = adapter.normalize_profile(raw_item)
            profile.metadata.setdefault("profile_source", "synthetic")
            profile.metadata.setdefault("dataset_source_type", "synthetic")
            profile.metadata.setdefault("authorization_basis", "synthetic_dataset")
            profile.metadata.setdefault("dataset_use", "research_baseline")
            profiles.append(profile)

        return profiles

    def collect(self) -> list[Finding]:
        """Preserve the original MVP interface for sample finding loading."""
        return self.collect_findings()
