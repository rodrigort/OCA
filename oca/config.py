"""Configuration and bundled-resource paths for source and frozen OCA builds."""

import json
import os
import re
import sys
from pathlib import Path


APP_NAME = "OpenCANAnalyzer"
CONFIG_FILENAME = "config.json"


def fit_window_geometry(saved_geometry, screen_width, screen_height):
    """Return a centered, screen-bounded window and minimum dimensions."""
    screen_width = max(320, int(screen_width))
    screen_height = max(320, int(screen_height))
    available_width = max(320, screen_width - 40)
    available_height = max(280, screen_height - 80)
    width = min(max(760, int(screen_width * 0.94)), 1600, available_width)
    height = min(max(520, int(screen_height * 0.86)), 900, available_height)

    match = re.match(r"^(\d+)x(\d+)", str(saved_geometry or ""))
    if match:
        width = min(max(min(980, available_width), int(match.group(1))), available_width)
        height = min(max(min(600, available_height), int(match.group(2))), available_height)

    x = max(0, (screen_width - width) // 2)
    y = max(0, (screen_height - height) // 2)
    return width, height, x, y, min(980, available_width), min(600, available_height)


def application_root():
    """Return the source root or the PyInstaller bundle resource directory."""
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        return Path(bundle)
    return Path(__file__).resolve().parent.parent


def executable_root():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return application_root()


def resource_path(relative_path):
    bundled = application_root() / relative_path
    if bundled.exists():
        return bundled
    installed = Path(sys.prefix) / "share" / "open-can-analyzer" / relative_path
    return installed if installed.exists() else bundled


def user_config_dir(platform=None, environ=None, home=None):
    platform = platform or sys.platform
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else Path(home)
    override = environ.get("OCA_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    if platform.startswith("win"):
        return Path(environ.get("LOCALAPPDATA", home / "AppData" / "Local")) / APP_NAME
    if platform == "darwin":
        return home / "Library" / "Application Support" / APP_NAME
    return Path(environ.get("XDG_CONFIG_HOME", home / ".config")) / "open-can-analyzer"


def portable_mode(environ=None, root=None):
    environ = os.environ if environ is None else environ
    root = executable_root() if root is None else Path(root)
    requested = str(environ.get("OCA_PORTABLE", "")).lower() in ("1", "true", "yes", "on")
    return requested or (root / ".portable").exists()


def config_path(environ=None, root=None, platform=None, home=None):
    root = executable_root() if root is None else Path(root)
    if portable_mode(environ=environ, root=root):
        return root / CONFIG_FILENAME
    return user_config_dir(platform=platform, environ=environ, home=home) / CONFIG_FILENAME


def load_config(path=None):
    path = config_path() if path is None else Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(data, path=None):
    path = config_path() if path is None else Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path
