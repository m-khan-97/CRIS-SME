"""Validate control-pack schema, parity and evaluator registrations for CI."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from cris_sme.controls.definitions import load_control_definitions
from cris_sme.controls.validation import validate_control_pack


def evaluator_inventory(root: Path) -> dict[tuple[str, str], set[str]]:
    inventory = {}
    for source in sorted((root / "src/cris_sme/controls").glob("*_controls.py")):
        for function in ast.parse(source.read_text()).body:
            if not isinstance(function, ast.FunctionDef):
                continue
            ids = {
                keyword.value.value
                for node in ast.walk(function) if isinstance(node, ast.Call)
                for keyword in node.keywords
                if keyword.arg == "control_id" and isinstance(keyword.value, ast.Constant)
                and isinstance(keyword.value.value, str)
            }
            if ids:
                inventory[source.stem, function.name] = ids
    return inventory


def validate(root: Path) -> int:
    path = root / "data/control_metadata_v2.json"
    schema = json.loads(path.with_suffix(".schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(json.loads(path.read_text()))
    definitions = load_control_definitions(path)
    validate_control_pack(definitions)
    inventory = evaluator_inventory(root)
    implemented = set().union(*inventory.values())
    if implemented != set(definitions):
        raise ValueError(f"Evaluator/registry mismatch: {sorted(implemented ^ set(definitions))}")
    for key, definition in definitions.items():
        declared = (definition.metadata["evaluator"], definition.metadata["evaluator_function"])
        if key not in inventory.get(declared, set()):
            raise ValueError(f"{key}: declared evaluator {declared} does not emit this control")
    return len(definitions)


if __name__ == "__main__":
    count = validate(Path(__file__).resolve().parents[1])
    print(f"Control metadata validated: {count} catalog, registry and evaluator IDs aligned.")
