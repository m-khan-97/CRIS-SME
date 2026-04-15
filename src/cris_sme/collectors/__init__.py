# Collector exports for mock and Azure-backed posture ingestion in CRIS-SME.
from .azure_collector import AzureCollector, AzureCollectorSettings
from .mock_collector import MockCollector
from .providers import ProviderProfileAdapter, get_profile_adapter

__all__ = [
    "AzureCollector",
    "AzureCollectorSettings",
    "MockCollector",
    "ProviderProfileAdapter",
    "get_profile_adapter",
]
