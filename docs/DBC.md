# DBC Guide

DBC support is optional:

```bash
python -m pip install -r requirements-dbc.txt
```

In OCA, choose **Load DBC**, select a `.dbc`, then receive frames described by that database.
The details panel shows decoded signals. The graph selector adds numeric signals for the
selected CAN ID; enumerated values remain visible in details but are not plotted.

`examples/demo.dbc` is synthetic and can be used with `examples/demo_capture.csv`. DBC frame
IDs must match OCA's current standard 11-bit range. Payload length, endianness, scaling,
signedness, multiplexing and units are interpreted by `cantools`.

DBC files frequently contain proprietary network definitions. Confirm redistribution rights,
remove private comments and identifiers, and do not commit a real database merely because it
contains no obvious personal data. Loading a DBC does not change bus bitrate or hardware mode.
