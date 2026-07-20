#!/usr/bin/env python3
"""Read-only syntax, JSON and translation-catalog validation for CI."""

import ast
import json
import string
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def main():
    python_files = sorted(ROOT.glob("*.py")) + sorted((ROOT / "oca").glob("*.py")) + sorted((ROOT / "tests").glob("*.py"))
    for path in python_files:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    for path in sorted(ROOT.rglob("*.json")):
        json.loads(path.read_text(encoding="utf-8"))

    english = json.loads((ROOT / "locales" / "en.json").read_text(encoding="utf-8"))
    portuguese = json.loads((ROOT / "locales" / "pt_BR.json").read_text(encoding="utf-8"))
    missing = sorted(set(english) - set(portuguese))
    extra = sorted(set(portuguese) - set(english))
    if missing or extra:
        raise SystemExit(f"translation key mismatch; missing={missing}, extra={extra}")

    formatter = string.Formatter()
    for key in english:
        en_fields = {name for _, name, _, _ in formatter.parse(english[key]) if name}
        pt_fields = {name for _, name, _, _ in formatter.parse(portuguese[key]) if name}
        if en_fields != pt_fields:
            raise SystemExit(f"translation placeholder mismatch for {key}: {en_fields} != {pt_fields}")

    used_keys = set()
    for path in python_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            function = node.func
            is_translation = (
                isinstance(function, ast.Name) and function.id == "tr"
                or isinstance(function, ast.Attribute) and function.attr == "tr"
            )
            if is_translation and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                used_keys.add(node.args[0].value)
    undefined = sorted(used_keys - set(english))
    if undefined:
        raise SystemExit(f"undefined translation keys: {undefined}")
    print(f"Validated {len(python_files)} Python files, JSON files and {len(english)} translation keys")


if __name__ == "__main__":
    main()
