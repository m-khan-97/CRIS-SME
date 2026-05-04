# Tests for machine-readable policy pack changelog loading.
from cris_sme.engine.policy_changelog import (
    load_policy_pack_changelog,
    summarize_policy_pack_changelog,
)
from cris_sme.policies import POLICY_PACK_VERSION


def test_policy_pack_changelog_loads_active_pack_entries() -> None:
    changelog = load_policy_pack_changelog()

    assert changelog.active_policy_pack_version == POLICY_PACK_VERSION
    assert changelog.entry_count >= 1
    assert any("IAM-005" in entry.control_ids for entry in changelog.entries)


def test_policy_pack_changelog_summary_counts_change_types() -> None:
    changelog = load_policy_pack_changelog()
    summary = summarize_policy_pack_changelog(changelog)

    assert summary["active_policy_pack_version"] == POLICY_PACK_VERSION
    assert summary["entry_count"] == changelog.entry_count
    assert summary["touched_control_count"] >= 1
    assert summary["change_type_counts"]
