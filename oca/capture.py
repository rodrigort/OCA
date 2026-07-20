"""Capture CSV reader used by replay and tests."""

import csv
import datetime as dt


def read_capture(path):
    frames = []
    with open(path, newline="", encoding="utf-8-sig") as capture_file:
        for row in csv.DictReader(capture_file):
            if row.get("type", "").upper() not in ("RX", "TX", "AUTO"):
                continue
            try:
                timestamp = dt.datetime.fromisoformat(row.get("timestamp", ""))
                can_id = int(row.get("id", "").lower().replace("0x", ""), 16)
                dlc = int(row.get("dlc", "0"))
                data = tuple(int(item, 16) for item in row.get("data", "").split())
            except (TypeError, ValueError):
                continue
            if not 0 <= can_id <= 0x7FF or not 0 <= dlc <= 8:
                continue
            if not dlc <= len(data) <= 8 or any(not 0 <= byte <= 0xFF for byte in data):
                continue
            frames.append((timestamp, can_id, dlc, data))
    return frames


def replay_delays(frames, minimum_spacing_ms=1):
    """Return nondecreasing desktop delays while preserving capture timing."""
    if not frames:
        return []
    first_time = frames[0][0]
    previous = -minimum_spacing_ms
    delays = []
    for timestamp, *_frame in frames:
        captured_delay = max(0, round((timestamp - first_time).total_seconds() * 1000.0))
        delay = max(previous + minimum_spacing_ms, captured_delay)
        delays.append(delay)
        previous = delay
    return delays
