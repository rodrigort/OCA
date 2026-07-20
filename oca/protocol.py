"""OCA text protocol encoder and decoder.

Protocol v1 remains supported so existing firmware and captures continue to work.
Protocol v2 adds device timestamps, TX sequence numbers and controller status.
"""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class CANFrame:
    direction: str
    can_id: int
    dlc: int
    data: Tuple[int, ...]
    timestamp_ms: Optional[int] = None
    sequence: Optional[int] = None
    raw: str = ""


@dataclass(frozen=True)
class CANStatus:
    rx_count: int
    tx_count: int
    dropped: int
    message_lost: int
    state: str
    tec: int
    rec: int
    mode: str = "ACTIVE"
    raw: str = ""


@dataclass(frozen=True)
class ProtocolMessage:
    kind: str
    frame: Optional[CANFrame] = None
    status: Optional[CANStatus] = None
    sequence: Optional[int] = None
    can_id: Optional[int] = None
    text: str = ""
    raw: str = ""


class ProtocolError(ValueError):
    """Raised when a serial line does not follow a supported OCA format."""


def _hex(value: str, maximum: int, field: str) -> int:
    try:
        parsed = int(value, 16)
    except (TypeError, ValueError) as exc:
        raise ProtocolError(f"invalid {field}") from exc
    if not 0 <= parsed <= maximum:
        raise ProtocolError(f"invalid {field}")
    return parsed


def _decimal(value: str, maximum: int, field: str) -> int:
    try:
        parsed = int(value, 10)
    except (TypeError, ValueError) as exc:
        raise ProtocolError(f"invalid {field}") from exc
    if not 0 <= parsed <= maximum:
        raise ProtocolError(f"invalid {field}")
    return parsed


def _frame(parts, raw, version):
    offset = 1
    timestamp_ms = None
    if version == 2:
        timestamp_ms = _decimal(parts[offset], 0xFFFFFFFF, "timestamp")
        offset += 1
    can_id = _hex(parts[offset], 0x7FF, "CAN ID")
    dlc = _decimal(parts[offset + 1], 8, "DLC")
    data = tuple(_hex(item, 0xFF, "data byte") for item in parts[offset + 2:offset + 10])
    if len(data) != 8:
        raise ProtocolError("RX frame must contain eight data fields")
    return CANFrame("RX", can_id, dlc, data, timestamp_ms=timestamp_ms, raw=raw)


def parse_line(line: str) -> ProtocolMessage:
    raw = line.strip()
    if not raw:
        raise ProtocolError("empty line")
    parts = raw.split(",")
    command = parts[0].upper()

    if command == "RX" and len(parts) == 11:
        return ProtocolMessage("FRAME", frame=_frame(parts, raw, 1), raw=raw)
    if command == "RX2" and len(parts) == 12:
        return ProtocolMessage("FRAME", frame=_frame(parts, raw, 2), raw=raw)
    if command == "STATUS" and len(parts) in (8, 9):
        state = parts[5].upper()
        mode = parts[8].upper() if len(parts) == 9 else "ACTIVE"
        if state not in ("OK", "ERROR_WARNING", "ERROR_PASSIVE", "BUS_OFF"):
            raise ProtocolError("invalid CAN state")
        if mode not in ("ACTIVE", "LISTEN"):
            raise ProtocolError("invalid CAN mode")
        status = CANStatus(
            rx_count=_decimal(parts[1], 0xFFFFFFFF, "RX count"),
            tx_count=_decimal(parts[2], 0xFFFFFFFF, "TX count"),
            dropped=_decimal(parts[3], 0xFFFFFFFF, "drop count"),
            message_lost=_decimal(parts[4], 0xFFFFFFFF, "message lost count"),
            state=state,
            tec=_decimal(parts[6], 255, "TEC"),
            rec=_decimal(parts[7], 255, "REC"),
            mode=mode,
            raw=raw,
        )
        return ProtocolMessage("STATUS", status=status, raw=raw)
    if command == "HELLO" and len(parts) >= 3:
        return ProtocolMessage("HELLO", text=",".join(parts[1:]), raw=raw)
    if command == "OK" and len(parts) >= 3 and parts[1].upper() == "TX":
        if len(parts) >= 4:
            return ProtocolMessage(
                "TX_OK", sequence=_decimal(parts[2], 0xFFFF, "sequence"),
                can_id=_hex(parts[3], 0x7FF, "CAN ID"), raw=raw,
            )
        return ProtocolMessage("TX_OK", can_id=_hex(parts[2], 0x7FF, "CAN ID"), raw=raw)
    if command == "OK" and len(parts) == 3 and parts[1].upper() == "LISTEN":
        if parts[2] not in ("0", "1"):
            raise ProtocolError("invalid listen-only mode")
        return ProtocolMessage("MODE", text="LISTEN" if parts[2] == "1" else "ACTIVE", raw=raw)
    if command == "ERR":
        return ProtocolMessage("ERROR", text=",".join(parts[1:]), raw=raw)
    return ProtocolMessage("TEXT", text=raw, raw=raw)


def build_tx(can_id: int, dlc: int, data, sequence=None) -> str:
    payload = tuple(int(value) for value in data)
    if not 0 <= can_id <= 0x7FF:
        raise ProtocolError("invalid CAN ID")
    if not 0 <= dlc <= 8:
        raise ProtocolError("invalid DLC")
    if len(payload) > 8 or any(not 0 <= value <= 0xFF for value in payload):
        raise ProtocolError("invalid data")
    payload += (0,) * (8 - len(payload))
    data_text = ",".join(f"{value:02X}" for value in payload)
    if sequence is None:
        return f"TX,{can_id:03X},{dlc},{data_text}\n"
    if not 0 <= sequence <= 0xFFFF:
        raise ProtocolError("invalid sequence")
    return f"TX2,{sequence},{can_id:03X},{dlc},{data_text}\n"
