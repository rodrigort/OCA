"""Optional DBC decoding support."""


class DBCError(RuntimeError):
    pass


class DBCDecoder:
    def __init__(self):
        self.database = None
        self.path = None

    def load(self, path):
        try:
            import cantools
        except ImportError as exc:
            raise DBCError("cantools_missing") from exc
        try:
            self.database = cantools.database.load_file(str(path))
            self.path = path
        except Exception as exc:
            raise DBCError(str(exc)) from exc

    def decode(self, can_id, data):
        if self.database is None:
            return ""
        try:
            message = self.database.get_message_by_frame_id(can_id)
            payload = bytes(tuple(data)[:message.length])
            signals = message.decode(payload, decode_choices=True, scaling=True)
        except Exception:
            return ""
        lines = [f"DBC: {message.name}"]
        for name, value in signals.items():
            signal = message.get_signal_by_name(name)
            unit = f" {signal.unit}" if signal.unit else ""
            lines.append(f"  {name}: {value}{unit}")
        return "\n".join(lines)

    def signal_choices(self, can_id):
        """Return signal names and units available for a CAN identifier."""
        if self.database is None:
            return []
        try:
            message = self.database.get_message_by_frame_id(can_id)
        except Exception:
            return []
        return [(signal.name, signal.unit or "") for signal in message.signals]

    def decode_signal(self, can_id, data, signal_name):
        """Decode one numeric signal for trend plotting."""
        if self.database is None:
            return None
        try:
            message = self.database.get_message_by_frame_id(can_id)
            payload = bytes(tuple(data)[:message.length])
            values = message.decode(payload, decode_choices=False, scaling=True)
            value = values[signal_name]
            if not isinstance(value, (int, float)):
                return None
            signal = message.get_signal_by_name(signal_name)
            return float(value), signal.unit or "", signal.minimum, signal.maximum
        except Exception:
            return None
