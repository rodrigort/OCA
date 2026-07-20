#!/usr/bin/env python3
"""Read-only syntax, JSON and translation-catalog validation for CI."""

import ast
import json
import string
from pathlib import Path
import xml.etree.ElementTree as ET


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

    firmware = ROOT / "firmware" / "CAN_Analyzer_XMC4700_Relax"
    required_public_files = [
        ROOT / "docs" / "images" / "oca-macos-live.png",
        ROOT / "docs" / "images" / "xmc4700-relax-kit.jpg",
        firmware / ".project",
        firmware / ".cproject",
        firmware / "Dave" / ".dconfig",
        firmware / "Dave" / "Generated" / "Config.xml",
        firmware / "Dave" / "Generated" / "CAN_NODE" / "can_node_conf.c",
        firmware / "main.c",
        firmware / "Lib_CAN_Analyzer.c",
        firmware / "Lib_USB_Command.c",
    ]
    missing_public_files = [str(path.relative_to(ROOT)) for path in required_public_files if not path.is_file()]
    if missing_public_files:
        raise SystemExit(f"missing public project files: {missing_public_files}")

    for path in [firmware / ".project", firmware / ".cproject", firmware / "Dave" / ".dconfig",
                 firmware / "Dave" / "Generated" / "Config.xml"]:
        ET.parse(path)

    generated_config = ET.parse(firmware / "Dave" / "Generated" / "Config.xml").getroot()
    if generated_config.attrib.get("Path"):
        raise SystemExit("firmware generated configuration contains an absolute project path")

    can_config = (firmware / "Dave" / "Generated" / "CAN_NODE" / "can_node_conf.c").read_text(
        encoding="utf-8", errors="replace"
    )
    if ".baudrate      = (uint32_t)(500 * 1000)" not in can_config:
        raise SystemExit("firmware CAN bitrate is not the documented 500 kbit/s")

    private_markers = [
        b"Rodrigo_V2",
        b"rodrigorodriguesteixeira",
        b"mosfet.01",
        b"PROJETO TRANSFESA",
        b"C:\\Users\\",
        b"/Users/",
    ]
    private_hits = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in {".git", "dist", "logs", "__pycache__"} for part in path.parts):
            continue
        content = path.read_bytes()
        if any(marker.lower() in content.lower() for marker in private_markers):
            private_hits.append(str(path.relative_to(ROOT)))
    if private_hits:
        raise SystemExit(f"private path or identity markers found: {private_hits}")

    print(
        f"Validated {len(python_files)} Python files, JSON/XML files, {len(english)} translation keys "
        "and the public XMC4700 firmware layout"
    )


if __name__ == "__main__":
    main()
