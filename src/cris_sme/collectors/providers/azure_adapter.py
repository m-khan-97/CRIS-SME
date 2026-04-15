# Azure provider adapter for normalizing Azure posture into the CRIS-SME core model.
from __future__ import annotations

from typing import Any

from cris_sme.collectors.providers.base import ProviderProfileAdapter
from cris_sme.models.cloud_profile import CloudProfile


class AzureProfileAdapter(ProviderProfileAdapter):
    """Normalize Azure posture records into the provider-neutral CloudProfile shape."""

    provider_name = "azure"

    def normalize_profile(self, raw_profile: dict[str, Any]) -> CloudProfile:
        """Validate a raw Azure record and enforce the Azure provider label."""
        normalized_profile = dict(raw_profile)
        normalized_profile.setdefault("provider", self.provider_name)

        if str(normalized_profile["provider"]).lower() != self.provider_name:
            raise ValueError(
                "AzureProfileAdapter received a non-Azure profile payload."
            )

        return CloudProfile.model_validate(normalized_profile)
