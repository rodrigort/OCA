import tempfile
import unittest
from pathlib import Path

from oca.capture import read_capture, replay_delays
from oca.config import resource_path


HEADER = "timestamp,type,id,dlc,data\n"


class CaptureTests(unittest.TestCase):
    def write_capture(self, content):
        temporary = tempfile.NamedTemporaryFile("w", suffix=".csv", encoding="utf-8", delete=False)
        temporary.write(content)
        temporary.close()
        self.addCleanup(lambda: Path(temporary.name).unlink(missing_ok=True))
        return Path(temporary.name)

    def test_read_valid_csv_frame(self):
        path = self.write_capture(HEADER + "2026-01-02T03:04:05.123,RX,0x101,2,11 22\n")
        frames = read_capture(path)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0][1:], (0x101, 2, (0x11, 0x22)))

    def test_skip_invalid_id_dlc_and_bytes(self):
        path = self.write_capture(
            HEADER
            + "2026-01-02T03:04:05,RX,0x800,1,00\n"
            + "2026-01-02T03:04:05,RX,0x100,9,00\n"
            + "2026-01-02T03:04:05,RX,0x100,2,00\n"
            + "2026-01-02T03:04:05,RX,0x100,1,100\n"
        )
        self.assertEqual(read_capture(path), [])

    def test_public_demo_capture(self):
        frames = read_capture(resource_path("examples/demo_capture.csv"))
        self.assertEqual(len(frames), 5)
        self.assertTrue(all(frame[1] == 0x101 for frame in frames))

    def test_replay_delays_preserve_long_captures(self):
        frames = read_capture(resource_path("examples/demo_capture.csv"))
        extended = [frames[0], (frames[0][0].replace(minute=2), *frames[0][1:])]
        self.assertEqual(replay_delays(extended), [0, 120000])


if __name__ == "__main__":
    unittest.main()
