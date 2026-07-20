"""Profile loading and validation for OCA."""

import json
from pathlib import Path


DEFAULT_PROFILE = {
    "profile_name": "Generic CAN",
    "baudrate_can": 500000,
    "ids": {},
    "auto_responses": [],
    "quick_tx": [],
}


class ProfileError(ValueError):
    def __init__(self, message, code="read", **context):
        super().__init__(message)
        self.code = code
        self.context = context


def normalize_id(value):
    text = str(value).strip()
    if text.lower().startswith("0x"):
        text = text[2:]
    parsed = int(text, 16)
    if not 0 <= parsed <= 0x7FF:
        raise ValueError("standard CAN ID outside 000..7FF")
    return f"0x{parsed:03X}"


def validate_profile(profile):
    if not isinstance(profile, dict):
        raise ProfileError("profile root must be an object", "root")
    merged = {**DEFAULT_PROFILE, **profile}
    if not isinstance(merged["profile_name"], str) or not merged["profile_name"].strip():
        raise ProfileError("profile_name must be a non-empty string", "name")
    if not isinstance(merged["baudrate_can"], int) or merged["baudrate_can"] <= 0:
        raise ProfileError("baudrate_can must be a positive integer", "bitrate")
    if not isinstance(merged["ids"], dict):
        raise ProfileError("ids must be an object", "ids")
    for key, description in merged["ids"].items():
        try:
            normalize_id(key)
        except (TypeError, ValueError) as exc:
            raise ProfileError(f"invalid CAN ID in profile: {key}", "invalid_id", value=key) from exc
        if not isinstance(description, str):
            raise ProfileError(f"description for {key} must be a string", "description", value=key)
    for collection in ("auto_responses", "quick_tx"):
        if not isinstance(merged[collection], list):
            raise ProfileError(f"{collection} must be an array", "collection", value=collection)
        for index, item in enumerate(merged[collection]):
            _validate_tx_item(item, collection, index)
    return merged


def _validate_tx_item(item, collection, index):
    label = f"{collection}[{index}]"
    if not isinstance(item, dict):
        raise ProfileError(f"{label} must be an object", "item", value=label)
    if collection == "auto_responses":
        try:
            normalize_id(item.get("rx_id"))
        except (TypeError, ValueError) as exc:
            raise ProfileError(f"invalid rx_id in {label}", "rx_id", value=label) from exc
        if "enabled" in item and not isinstance(item["enabled"], bool):
            raise ProfileError(f"enabled in {label} must be boolean", "enabled", value=label)
    try:
        normalize_id(item.get("tx_id"))
    except (TypeError, ValueError) as exc:
        raise ProfileError(f"invalid tx_id in {label}", "tx_id", value=label) from exc
    dlc = item.get("dlc")
    if not isinstance(dlc, int) or not 0 <= dlc <= 8:
        raise ProfileError(f"dlc in {label} must be an integer from 0 to 8", "dlc", value=label)
    data = item.get("data")
    if not isinstance(data, list) or len(data) > 8 or len(data) < dlc:
        raise ProfileError(f"data in {label} must contain between DLC and 8 bytes", "data", value=label)
    for byte in data:
        try:
            value = int(str(byte), 0) if not isinstance(byte, int) else byte
        except (TypeError, ValueError) as exc:
            raise ProfileError(f"invalid data byte in {label}: {byte}", "byte", value=byte, item=label) from exc
        if not 0 <= value <= 0xFF:
            raise ProfileError(f"invalid data byte in {label}: {byte}", "byte", value=byte, item=label)
    for text_field in ("label", "description"):
        if text_field in item and not isinstance(item[text_field], str):
            raise ProfileError(
                f"{text_field} in {label} must be a string", "text", field=text_field, value=label
            )


def load_profile(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return validate_profile(data)
    except ProfileError:
        raise
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ProfileError(str(exc), "read", error=str(exc)) from exc
