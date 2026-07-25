# CLI for managing the CRIS-SME operational finding mute-rule registry.
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from cris_sme.engine.lifecycle import DEFAULT_MUTE_RULE_REGISTRY_PATH
from cris_sme.models.platform import MuteRule


def _load_rules(path: Path) -> list[dict]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, list) else []


def _save_rules(path: Path, rules: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rules, indent=2) + "\n", encoding="utf-8")


def cmd_list(args: argparse.Namespace) -> int:
    rules = _load_rules(args.path)
    if not rules:
        print("No mute rules registered.")
        return 0
    for rule in rules:
        state = "enabled" if rule.get("enabled", True) else "disabled"
        print(
            f"{rule['rule_id']}  [{state}]  {rule['name']!r}  "
            f"control_id={rule.get('control_id') or '*'}  "
            f"provider={rule.get('provider') or '*'}  "
            f"scope={rule.get('scope_pattern', '*')}  "
            f"finding_id={rule.get('finding_id_pattern') or '*'}  "
            f"expires_at={rule.get('expires_at') or 'never'}"
        )
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    rules = _load_rules(args.path)
    if any(rule["rule_id"] == args.rule_id for rule in rules):
        print(f"Mute rule '{args.rule_id}' already exists.")
        return 1

    rule = MuteRule(
        rule_id=args.rule_id,
        name=args.name,
        enabled=not args.disabled,
        control_id=args.control_id,
        provider=args.provider,
        scope_pattern=args.scope_pattern,
        finding_id_pattern=args.finding_id_pattern,
        reason=args.reason,
        created_by=args.created_by,
        created_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        expires_at=args.expires_at,
    )
    rules.append(rule.model_dump(mode="json"))
    _save_rules(args.path, rules)
    print(f"Added mute rule '{rule.rule_id}'.")
    return 0


def cmd_enable(args: argparse.Namespace) -> int:
    return _set_enabled(args, enabled=True)


def cmd_disable(args: argparse.Namespace) -> int:
    return _set_enabled(args, enabled=False)


def _set_enabled(args: argparse.Namespace, *, enabled: bool) -> int:
    rules = _load_rules(args.path)
    for rule in rules:
        if rule["rule_id"] == args.rule_id:
            rule["enabled"] = enabled
            _save_rules(args.path, rules)
            print(f"Mute rule '{args.rule_id}' {'enabled' if enabled else 'disabled'}.")
            return 0
    print(f"Mute rule '{args.rule_id}' not found.")
    return 1


def cmd_remove(args: argparse.Namespace) -> int:
    rules = _load_rules(args.path)
    remaining = [rule for rule in rules if rule["rule_id"] != args.rule_id]
    if len(remaining) == len(rules):
        print(f"Mute rule '{args.rule_id}' not found.")
        return 1
    _save_rules(args.path, remaining)
    print(f"Removed mute rule '{args.rule_id}'.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage CRIS-SME operational finding mute rules.",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_MUTE_RULE_REGISTRY_PATH,
        help="Path to the mute rule registry JSON file.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List registered mute rules.").set_defaults(
        func=cmd_list
    )

    add_parser = subparsers.add_parser("add", help="Add a new mute rule.")
    add_parser.add_argument("rule_id", help="Unique identifier for the rule.")
    add_parser.add_argument("name", help="Human-readable rule name.")
    add_parser.add_argument("reason", help="Why this finding pattern is muted.")
    add_parser.add_argument("created_by", help="Who created this rule.")
    add_parser.add_argument("--control-id", default=None, help="Match a specific control ID.")
    add_parser.add_argument("--provider", default=None, help="Match a specific provider.")
    add_parser.add_argument(
        "--scope-pattern",
        default="*",
        help="fnmatch pattern against the finding's resource_scope (default: '*').",
    )
    add_parser.add_argument(
        "--finding-id-pattern",
        default=None,
        help="fnmatch pattern against the finding_id.",
    )
    add_parser.add_argument(
        "--expires-at",
        default=None,
        help="ISO-8601 timestamp after which this rule no longer applies.",
    )
    add_parser.add_argument(
        "--disabled",
        action="store_true",
        help="Create the rule in a disabled state.",
    )
    add_parser.set_defaults(func=cmd_add)

    enable_parser = subparsers.add_parser("enable", help="Enable a mute rule.")
    enable_parser.add_argument("rule_id")
    enable_parser.set_defaults(func=cmd_enable)

    disable_parser = subparsers.add_parser("disable", help="Disable a mute rule.")
    disable_parser.add_argument("rule_id")
    disable_parser.set_defaults(func=cmd_disable)

    remove_parser = subparsers.add_parser("remove", help="Remove a mute rule.")
    remove_parser.add_argument("rule_id")
    remove_parser.set_defaults(func=cmd_remove)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
