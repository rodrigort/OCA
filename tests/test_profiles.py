import unittest

from oca.config import resource_path
from oca.profiles import ProfileError, load_profile, normalize_id, validate_profile


class ProfileTests(unittest.TestCase):
    def test_normalize_standard_id(self):
        self.assertEqual(normalize_id("101"), "0x101")

    def test_reject_extended_id(self):
        with self.assertRaises(ValueError):
            normalize_id("800")

    def test_profile_defaults(self):
        profile = validate_profile({"profile_name": "Test"})
        self.assertEqual(profile["baudrate_can"], 500000)

    def test_reject_invalid_ids(self):
        with self.assertRaises(ProfileError):
            validate_profile({"profile_name": "Test", "ids": {"0x900": "bad"}})

    def test_validate_complete_transmit_item(self):
        profile = validate_profile({
            "profile_name": "Test",
            "quick_tx": [{"tx_id": "0x101", "dlc": 2, "data": ["0x11", "0x22"]}],
        })
        self.assertEqual(profile["quick_tx"][0]["dlc"], 2)

    def test_reject_short_or_out_of_range_data(self):
        with self.assertRaises(ProfileError):
            validate_profile({
                "profile_name": "Test",
                "quick_tx": [{"tx_id": "0x101", "dlc": 2, "data": ["0x100"]}],
            })

    def test_public_profiles_are_valid(self):
        profiles = resource_path("profiles")
        for path in profiles.glob("*.json"):
            with self.subTest(path=path.name):
                self.assertTrue(load_profile(path)["profile_name"])


if __name__ == "__main__":
    unittest.main()
