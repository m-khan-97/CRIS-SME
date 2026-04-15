# Placeholder AWS adapter for the future provider-neutral expansion of CRIS-SME.
from __future__ import annotations

from typing import Any

from cris_sme.collectors.providers.base import ProviderProfileAdapter
from cris_sme.models.cloud_profile import CloudProfile


class AwsProfileAdapter(ProviderProfileAdapter):
    """Normalize AWS-style raw posture records into the CRIS-SME core profile shape."""

    provider_name = "aws"

    def normalize_profile(self, raw_profile: dict[str, Any]) -> CloudProfile:
        """Validate a pre-normalized AWS raw profile once the collector is implemented."""
        candidate = dict(raw_profile)
        candidate["provider"] = self.provider_name
        return CloudProfile.model_validate(candidate)
