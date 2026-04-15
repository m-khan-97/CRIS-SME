# Provider adapter contract for normalizing provider-specific posture into CloudProfile.
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from cris_sme.models.cloud_profile import CloudProfile


class ProviderProfileAdapter(ABC):
    """Normalize raw provider posture records into the provider-neutral CloudProfile."""

    provider_name: str

    @abstractmethod
    def normalize_profile(self, raw_profile: dict[str, Any]) -> CloudProfile:
        """Validate and normalize one raw provider posture record."""
