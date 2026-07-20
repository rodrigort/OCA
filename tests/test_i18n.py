import json
import tempfile
import unittest
from pathlib import Path

from oca.i18n import Translator, resolve_language, system_language


class LanguageTests(unittest.TestCase):
    def test_portuguese_system_locales(self):
        self.assertEqual(system_language("pt-BR"), "pt_BR")
        self.assertEqual(system_language("pt_PT.UTF-8"), "pt_BR")
        self.assertEqual(system_language("Portuguese_Brazil.1252"), "pt_BR")

    def test_other_system_locale_uses_english(self):
        self.assertEqual(system_language("es_ES"), "en")

    def test_manual_selection_and_invalid_fallback(self):
        self.assertEqual(resolve_language("pt_BR", "en_US"), "pt_BR")
        self.assertEqual(resolve_language("unknown", "pt_BR"), "en")

    def test_missing_translation_falls_back_to_english(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "en.json").write_text(json.dumps({"present": "English", "only_en": "Fallback"}), encoding="utf-8")
            (root / "pt_BR.json").write_text(json.dumps({"present": "Português"}), encoding="utf-8")
            translator = Translator(root, "pt_BR")
            self.assertEqual(translator("present"), "Português")
            self.assertEqual(translator("only_en"), "Fallback")
            self.assertEqual(translator("unknown_key"), "unknown_key")


if __name__ == "__main__":
    unittest.main()
