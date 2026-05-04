# Policy pack changelog loading for policy drift traceability.
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from cris_sme.models.platform import (
    PolicyPackChangelog,
    PolicyPackChangelogEntry,
)
from cris_sme.policies import POLICY_PACK_VERSION


DEFAULT_POLICY_CHANGELOG_PATH = Path("data/policy_pack_changelog.json")


@lru_cache(maxsize=1)
def load_policy_pack_changelog(
    path: str | Path = DEFAULT_POLICY_CHANGELOG_PATH,
) -> PolicyPackChangelog:
    """Load the machine-readable policy pack changelog."""
    changelog_path = Path(path)
    if not changelog_path.exists():
        return PolicyPackChangelog(
            active_policy_pack_version=POLICY_PACK_VERSION,
            entry_count=0,
            entries=[],
        )
    raw = json.loads(changelog_path.read_text(encoding="utf-8"))
    entries = [
        PolicyPackChangelogEntry.model_validate(item)
        for item in raw
        if isinstance(item, dict)
    ]
    entries.sort(key=lambda item: (item.version, item.released_at, item.title))
    return PolicyPackChangelog(
        active_policy_pack_version=POLICY_PACK_VERSION,
        entry_count=len(entries),
        entries=entries,
    )


def summarize_policy_pack_changelog(
    changelog: PolicyPackChangelog | dict[str, object],
) -> dict[str, object]:
    """Build compact changelog metadata for dashboards and API payloads."""
    raw = changelog if isinstance(changelog, dict) else changelog.model_dump(mode="json")
    entries = raw.get("entries", [])
    touched_controls: set[str] = set()
    change_type_counts: dict[str, int] = {}
    if isinstance(entries, list):
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            change_type = str(entry.get("change_type", "unknown"))
            change_type_counts[change_type] = change_type_counts.get(change_type, 0) + 1
            for control_id in entry.get("control_ids", []):
                if str(control_id).strip():
                    touched_controls.add(str(control_id))
    return {
        "changelog_schema_version": raw.get("changelog_schema_version"),
        "active_policy_pack_version": raw.get("active_policy_pack_version"),
        "entry_count": int(raw.get("entry_count", 0)),
        "touched_control_count": len(touched_controls),
        "change_type_counts": change_type_counts,
    }
