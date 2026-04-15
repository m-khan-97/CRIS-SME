# Unit tests for provider adapter routing and profile normalization in CRIS-SME.
from cris_sme.collectors.mock_collector import MockCollector
from cris_sme.collectors.providers import get_profile_adapter
from cris_sme.models.cloud_profile import CloudProfile


def test_get_profile_adapter_returns_azure_adapter() -> None:
    adapter = get_profile_adapter("azure")

    assert adapter.provider_name == "azure"


def test_get_profile_adapter_raises_for_unknown_provider() -> None:
    try:
        get_profile_adapter("aws")
    except ValueError as exc:
        assert "Unsupported cloud provider" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported provider")


def test_mock_collector_normalizes_profiles_through_provider_adapters() -> None:
    collector = MockCollector()

    profiles = collector.collect_profiles()

    assert profiles
    assert all(isinstance(profile, CloudProfile) for profile in profiles)
    assert {profile.provider for profile in profiles} == {"azure"}
