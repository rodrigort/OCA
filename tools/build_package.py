#!/usr/bin/env python3
"""Build the current platform's standalone OCA application with PyInstaller."""

import os
from pathlib import Path

import PyInstaller.__main__


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def data_argument(source, destination):
    return f"{PROJECT_ROOT / source}{os.pathsep}{destination}"


def main():
    PyInstaller.__main__.run([
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name=OpenCANAnalyzer",
        "--collect-all=cantools",
        f"--add-data={data_argument('profiles', 'profiles')}",
        f"--add-data={data_argument('locales', 'locales')}",
        f"--add-data={data_argument('examples', 'examples')}",
        str(PROJECT_ROOT / "can_analyzer_gui.py"),
    ])


if __name__ == "__main__":
    main()
