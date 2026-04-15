# Central configuration helpers for selecting collectors and runtime settings in CRIS-SME.
from __future__ import annotations

import os

from cris_sme.collectors.azure_collector import AzureCollectorSettings


def get_collector_mode() -> str:
    """Return the configured collector mode, defaulting to mock for safe local execution."""
    return os.getenv("CRIS_SME_COLLECTOR", "mock").strip().lower()


def get_azure_collector_settings() -> AzureCollectorSettings:
    """Build Azure collector settings from environment variables."""
    return AzureCollectorSettings(
        subscription_id=_get_optional_env("AZURE_SUBSCRIPTION_ID"),
        organization_name=os.getenv(
            "CRIS_SME_AZURE_ORGANIZATION_NAME",
            "Azure SME Tenant",
        ),
        sector=os.getenv("CRIS_SME_AZURE_SECTOR", "SME"),
        tenant_scope=_get_optional_env("CRIS_SME_AZURE_TENANT_SCOPE"),
        organization_id=_get_optional_env("CRIS_SME_AZURE_ORGANIZATION_ID"),
    )


def _get_optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None

    stripped = value.strip()
    return stripped or None
