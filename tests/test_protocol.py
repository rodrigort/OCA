import unittest

from oca.protocol import ProtocolError, build_tx, parse_line


class ProtocolTests(unittest.TestCase):
    def test_parse_legacy_rx(self):
        message = parse_line("RX,101,8,10,20,30,40,50,60,70,80")
        self.assertEqual(message.kind, "FRAME")
        self.assertEqual(message.frame.can_id, 0x101)
        self.assertIsNone(message.frame.timestamp_ms)
        self.assertEqual(message.frame.data[-1], 0x80)

    def test_parse_v2_rx(self):
        message = parse_line("RX2,1234,301,8,A1,B2,C3,D4,E5,F6,07,18")
        self.assertEqual(message.frame.timestamp_ms, 1234)
        self.assertEqual(message.frame.can_id, 0x301)

    def test_parse_status(self):
        message = parse_line("STATUS,100,4,2,1,ERROR_WARNING,96,3,LISTEN")
        self.assertEqual(message.status.dropped, 2)
        self.assertEqual(message.status.state, "ERROR_WARNING")
        self.assertEqual(message.status.mode, "LISTEN")

    def test_parse_v2_tx_confirmation(self):
        message = parse_line("OK,TX,42,201")
        self.assertEqual(message.sequence, 42)
        self.assertEqual(message.can_id, 0x201)

    def test_build_v2_tx(self):
        command = build_tx(0x201, 2, [0x11, 0x22], sequence=7)
        self.assertEqual(command, "TX2,7,201,2,11,22,00,00,00,00,00,00\n")

    def test_reject_invalid_frame(self):
        with self.assertRaises(ProtocolError):
            parse_line("RX2,1,800,8,00,00,00,00,00,00,00,00")

    def test_reject_invalid_status_enums(self):
        with self.assertRaises(ProtocolError):
            parse_line("STATUS,1,2,0,0,UNKNOWN,0,0,ACTIVE")
        with self.assertRaises(ProtocolError):
            parse_line("STATUS,1,2,0,0,OK,0,0,INVALID")

    def test_reject_invalid_listen_ack(self):
        with self.assertRaises(ProtocolError):
            parse_line("OK,LISTEN,2")


if __name__ == "__main__":
    unittest.main()
