# Central configuration helpers for selecting collectors and runtime settings in CRIS-SME.
from __future__ import annotations

import os

from cris_sme.collectors.azure_collector import AzureCollectorSettings
from cris_sme.reporting.narrator import NarratorSettings


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


def get_narrator_settings() -> NarratorSettings:
    """Build narrator settings from environment variables."""
    return NarratorSettings(
        enabled=_get_bool_env("CRIS_SME_ENABLE_NARRATOR", default=False),
        provider=os.getenv("CRIS_SME_NARRATOR_PROVIDER", "anthropic").strip().lower(),
        api_key=_get_optional_env("ANTHROPIC_API_KEY"),
        model=os.getenv("CRIS_SME_NARRATOR_MODEL", "claude-sonnet-4-20250514").strip(),
        max_tokens=int(os.getenv("CRIS_SME_NARRATOR_MAX_TOKENS", "1400")),
        temperature=float(os.getenv("CRIS_SME_NARRATOR_TEMPERATURE", "0.2")),
        timeout_seconds=int(os.getenv("CRIS_SME_NARRATOR_TIMEOUT_SECONDS", "45")),
    )


def _get_optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None

    stripped = value.strip()
    return stripped or None


def _get_bool_env(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default
