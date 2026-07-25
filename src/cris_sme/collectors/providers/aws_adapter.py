# AWS provider adapter for normalizing AWS posture into the CRIS-SME core model.
from __future__ import annotations

from typing import Any

from cris_sme.collectors.providers.base import ProviderProfileAdapter
from cris_sme.models.cloud_profile import CloudProfile


class AwsProfileAdapter(ProviderProfileAdapter):
    """Normalize AWS posture records into the provider-neutral CloudProfile shape."""

    provider_name = "aws"

    def normalize_profile(self, raw_profile: dict[str, Any]) -> CloudProfile:
        """Validate a raw AWS record and enforce the AWS provider label."""
        normalized_profile = dict(raw_profile)
        normalized_profile.setdefault("provider", self.provider_name)

        if str(normalized_profile["provider"]).lower() != self.provider_name:
            raise ValueError(
                "AwsProfileAdapter received a non-AWS profile payload."
            )

        return CloudProfile.model_validate(normalized_profile)
