# Provider adapter registry for routing raw posture records to the correct normalizer.
from __future__ import annotations

from cris_sme.collectors.providers.azure_adapter import AzureProfileAdapter
from cris_sme.collectors.providers.base import ProviderProfileAdapter


_PROFILE_ADAPTERS: dict[str, ProviderProfileAdapter] = {
    "azure": AzureProfileAdapter(),
}


def get_profile_adapter(provider: str) -> ProviderProfileAdapter:
    """Return the registered adapter for a given provider identifier."""
    normalized_provider = provider.strip().lower()
    adapter = _PROFILE_ADAPTERS.get(normalized_provider)
    if adapter is None:
        raise ValueError(
            f"Unsupported cloud provider '{provider}'. "
            "Register a provider adapter before collecting profiles."
        )
    return adapter
