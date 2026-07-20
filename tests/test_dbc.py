import unittest

from oca.config import resource_path
from oca.dbc import DBCDecoder, DBCError


class FakeSignal:
    def __init__(self, name, unit="", minimum=None, maximum=None):
        self.name = name
        self.unit = unit
        self.minimum = minimum
        self.maximum = maximum


class FakeMessage:
    length = 8

    def __init__(self):
        self.signals = [FakeSignal("Speed", "km/h", 0, 250)]

    def decode(self, _payload, decode_choices=True, scaling=True):
        return {"Speed": 42.5}

    def get_signal_by_name(self, name):
        return next(signal for signal in self.signals if signal.name == name)


class FakeDatabase:
    def get_message_by_frame_id(self, can_id):
        if can_id != 0x101:
            raise KeyError(can_id)
        return FakeMessage()


class DBCDecoderTests(unittest.TestCase):
    def setUp(self):
        self.decoder = DBCDecoder()
        self.decoder.database = FakeDatabase()

    def test_signal_choices_include_unit(self):
        self.assertEqual(self.decoder.signal_choices(0x101), [("Speed", "km/h")])

    def test_decode_numeric_signal_for_graph(self):
        result = self.decoder.decode_signal(0x101, [0] * 8, "Speed")
        self.assertEqual(result, (42.5, "km/h", 0, 250))

    def test_public_demo_dbc(self):
        decoder = DBCDecoder()
        try:
            decoder.load(resource_path("examples/demo.dbc"))
        except DBCError as exc:
            if str(exc) == "cantools_missing":
                self.skipTest("cantools is not installed")
            raise
        speed = decoder.decode_signal(0x101, [0x10, 0x27, 0x50, 0, 0, 0, 0, 0], "Speed")
        self.assertEqual(speed[0], 1000.0)
        self.assertEqual(speed[1], "km/h")


if __name__ == "__main__":
    unittest.main()
