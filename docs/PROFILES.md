# Profile Guide

Profiles are UTF-8 JSON objects that keep CAN IDs and bench presets outside application code.
Use `profiles/generic.json` as a safe starting point.

```json
{
  "profile_name": "Example bench",
  "baudrate_can": 500000,
  "ids": {"0x101": "Status"},
  "auto_responses": [],
  "quick_tx": [
    {
      "label": "Send test",
      "tx_id": "0x100",
      "dlc": 2,
      "data": ["0x11", "0x22"],
      "description": "Synthetic bench command"
    }
  ]
}
```

`profile_name` must be non-empty, `baudrate_can` positive, and IDs must be standard `0x000`
through `0x7FF`. Each TX item requires a valid `tx_id`, integer DLC 0–8 and between DLC and
eight valid bytes. An automatic response also requires `rx_id` and may contain `enabled`.

Automatic responses are global-off by default. Enabling them can transmit immediately when a
matching RX ID arrives. Use only synthetic or authorized data, prefer listen-only during
initial inspection, and never commit customer or vehicle-specific profiles without permission.

The visual editor currently changes profile name, bitrate and ID descriptions. Edit advanced
TX/response rules in a text editor and run `python tools/validate_project.py` plus the tests.
