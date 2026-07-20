"""Small JSON-based internationalization layer used by OCA."""

import json
import locale
import os
from pathlib import Path


SUPPORTED_LANGUAGES = ("en", "pt_BR")
DEFAULT_LANGUAGE = "en"


def system_language(system_locale=None):
    """Return the supported language matching the operating-system locale."""
    if system_locale is None:
        system_locale = locale.getlocale()[0] or os.environ.get("LANG", "")
    normalized = str(system_locale or "").replace("-", "_").lower()
    portuguese = (
        normalized.startswith("pt_br")
        or normalized.startswith("pt_pt")
        or normalized.startswith("portuguese_brazil")
        or normalized.startswith("portuguese_portugal")
    )
    return "pt_BR" if portuguese else "en"


def resolve_language(selection="auto", system_locale=None):
    """Resolve auto/manual settings to a supported translation code."""
    if selection in (None, "", "auto"):
        return system_language(system_locale)
    normalized = str(selection).replace("-", "_")
    if normalized.lower() in ("pt", "pt_br", "pt_pt"):
        return "pt_BR"
    if normalized.lower().startswith("en"):
        return "en"
    return DEFAULT_LANGUAGE


class Translator:
    """Load the requested catalog and fall back to English for missing keys."""

    def __init__(self, locales_dir, selection="auto", system_locale=None):
        self.locales_dir = Path(locales_dir)
        self.selection = selection or "auto"
        self.language = resolve_language(self.selection, system_locale)
        self._english = self._load("en")
        self._catalog = self._english if self.language == "en" else self._load(self.language)

    def _load(self, language):
        path = self.locales_dir / f"{language}.json"
        try:
            catalog = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            if language == DEFAULT_LANGUAGE:
                raise RuntimeError(f"cannot load English translations: {exc}") from exc
            return {}
        if not isinstance(catalog, dict):
            raise RuntimeError(f"translation catalog must be an object: {path}")
        return catalog

    def __call__(self, key, **values):
        text = self._catalog.get(key, self._english.get(key, key))
        try:
            return str(text).format(**values)
        except (KeyError, ValueError):
            return str(text)
