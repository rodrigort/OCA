import tempfile
import unittest
from pathlib import Path

from oca.config import config_path, fit_window_geometry, load_config, save_config, user_config_dir


class ConfigTests(unittest.TestCase):
    def test_portable_environment_keeps_config_beside_application(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = config_path(environ={"OCA_PORTABLE": "1"}, root=root)
            self.assertEqual(path, root / "config.json")

    def test_platform_specific_user_paths(self):
        home = Path("/home/tester")
        self.assertEqual(
            user_config_dir(platform="linux", environ={}, home=home),
            home / ".config" / "open-can-analyzer",
        )
        self.assertEqual(
            user_config_dir(platform="darwin", environ={}, home=home),
            home / "Library" / "Application Support" / "OpenCANAnalyzer",
        )

    def test_config_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "config.json"
            save_config({"language": "auto", "port": ""}, path)
            self.assertEqual(load_config(path), {"language": "auto", "port": ""})

    def test_window_geometry_is_centered_and_bounded(self):
        width, height, x, y, minimum_width, minimum_height = fit_window_geometry(
            "3000x2000+100+100", 1440, 900
        )
        self.assertEqual((width, height), (1400, 820))
        self.assertEqual((x, y), (20, 40))
        self.assertLessEqual(minimum_width, width)
        self.assertLessEqual(minimum_height, height)

    def test_window_geometry_handles_small_screens(self):
        width, height, x, y, _minimum_width, _minimum_height = fit_window_geometry("", 800, 600)
        self.assertLessEqual(width, 760)
        self.assertLessEqual(height, 520)
        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)


if __name__ == "__main__":
    unittest.main()
