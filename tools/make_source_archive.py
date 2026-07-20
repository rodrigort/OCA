#!/usr/bin/env python3
"""Create a clean, portable source ZIP with a validated project layout."""

from __future__ import annotations

import hashlib
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parent.parent
VERSION = "0.4.0"
ARCHIVE_ROOT = f"Open-CAN-Analyzer-{VERSION}"
OUTPUT_DIR = ROOT / "dist"
OUTPUT = OUTPUT_DIR / f"{ARCHIVE_ROOT}-source.zip"

EXCLUDED_PARTS = {
    ".git",
    ".github-cache",
    ".idea",
    ".pytest_cache",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "dist",
    "env",
    "logs",
    "venv",
}
EXCLUDED_NAMES = {".coverage", ".DS_Store", ".portable", "config.json", "Thumbs.db"}
EXCLUDED_SUFFIXES = {".egg-info", ".log", ".pyc", ".pyo", ".spec", "~"}


def is_public_file(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if path.name in EXCLUDED_NAMES or any(path.name.endswith(suffix) for suffix in EXCLUDED_SUFFIXES):
        return False
    if path.suffix.lower() in {".csv", ".dbc"} and relative.parts[0] != "examples":
        return False
    return path.is_file()


def add_file(archive: zipfile.ZipFile, path: Path) -> None:
    relative = path.relative_to(ROOT).as_posix()
    info = zipfile.ZipInfo.from_file(path, f"{ARCHIVE_ROOT}/{relative}")
    info.create_system = 3
    mode = 0o755 if path.suffix == ".sh" else 0o644
    info.external_attr = mode << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, path.read_bytes())


def main() -> None:
    required = [
        ROOT / "can_analyzer_gui.py",
        ROOT / "pyproject.toml",
        ROOT / "oca" / "__init__.py",
        ROOT / "oca" / "config.py",
        ROOT / "oca" / "i18n.py",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise SystemExit(f"Cannot package an incomplete project; missing: {', '.join(missing)}")

    files = sorted(path for path in ROOT.rglob("*") if is_public_file(path))
    OUTPUT_DIR.mkdir(exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w") as archive:
        for path in files:
            add_file(archive, path)

    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    checksum = OUTPUT.with_suffix(OUTPUT.suffix + ".sha256")
    checksum.write_text(f"{digest}  {OUTPUT.name}\n", encoding="ascii")
    print(f"Created {OUTPUT} ({len(files)} files)")
    print(f"SHA-256: {digest}")


if __name__ == "__main__":
    main()
