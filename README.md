# Open CAN Analyzer (OCA)

[Português do Brasil](README.pt-BR.md)

Open CAN Analyzer is an open-source desktop application for receiving, inspecting,
transmitting, recording, decoding and replaying Classical CAN traffic through a serial USB
adapter that implements the documented OCA text protocol. The application is written in
Python/Tkinter and targets Windows, Linux and macOS.

OCA is an educational and bench-development tool. It is not a safety-certified diagnostic
product, a vehicle repair authority, or a direct replacement for a commercial validation
suite. Current desktop version: **0.4.0**.

## Features

- Automatic serial-port discovery without a fixed COM number.
- OCA protocol v1 compatibility and v2 negotiation, timestamps and diagnostics.
- Standard 11-bit Classical CAN RX and TX with DLC 0 through 8.
- Traffic, latest-frame-per-ID and time-series graph views.
- ID/range, direction and text filters.
- JSON profiles, quick TX presets and optional automatic responses.
- Optional DBC loading, signal decoding and numeric signal plotting through `cantools`.
- CSV recording, CSV replay, visible-row export and candump export.
- Hardware listen-only control when supported by protocol v2 firmware.
- A local synthetic graph demo that never connects to or transmits on CAN.
- English and Brazilian Portuguese UI with OS detection and persistent manual selection.

## Hardware and protocol

OCA requires a serial USB CAN adapter or firmware implementation that speaks the ASCII,
line-oriented protocol in [docs/PROTOCOL.md](docs/PROTOCOL.md). The repository does not
contain or require a particular microcontroller firmware. A compatible device normally
provides:

- a USB CDC/virtual serial port;
- a Classical CAN controller and appropriate transceiver;
- CANH, CANL and a common reference where required;
- correct bus bitrate, termination and electrical protection.

The current protocol supports standard 11-bit IDs only. A typical received frame is:

```text
RX2,1234,101,8,10,20,30,40,50,60,70,80
```

## Install and run

Python 3.9 or newer is required. Tkinter is included with standard Windows and macOS Python
installers; some Linux distributions package it separately as `python3-tk`.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: . .venv/bin/activate
python -m pip install -r requirements.txt
python can_analyzer_gui.py
```

Optional DBC support:

```bash
python -m pip install -r requirements-dbc.txt
```

Launchers are also provided:

```text
executar_can_analyzer_gui.bat       Windows GUI
executar_can_analyzer_serial.bat    Windows terminal
./run_can_analyzer_gui.sh           Linux/macOS GUI
```

Terminal examples:

```bash
python can_analyzer_serial.py --list
python can_analyzer_serial.py --port COM7
python can_analyzer_serial.py --port /dev/ttyACM0 --csv capture.csv
```

If no port is listed, install `pyserial`, reconnect the adapter, check operating-system
permissions and make sure another application is not holding the port.

For the XMC4700 Relax Kit on Windows, follow the official-driver procedure in
[docs/WINDOWS_DRIVER.md](docs/WINDOWS_DRIVER.md). macOS and Linux normally use their built-in
generic USB driver for the on-board J-Link interface.

## First use without hardware

Open the **Graphs** tab and select **Local demo**. OCA creates a clearly identified synthetic
curve under ID `0x7FE`; no serial connection is opened and no frame is transmitted. Public,
synthetic files are available in `examples/demo_capture.csv`, `examples/demo.dbc` and the
profiles directory.

## Graphs

The graph collects received frames by CAN ID. Select an ID and byte `B0` through `B7`, or a
numeric DBC signal. The window control sets the visible interval; autoscale follows visible
values, while fixed byte scale uses 0–255. Pausing the graph pauses drawing only—capture and
history continue. History is bounded and visually downsampled to keep the UI responsive.

## Profiles and DBC

Profiles store public, adapter-independent labels, quick transmissions and automatic response
rules. Start with `profiles/generic.json`; automatic responses are disabled globally by
default. See [docs/PROFILES.md](docs/PROFILES.md).

DBC loading is optional. Install `cantools`, choose **Load DBC**, and select a database you are
authorized to use. Numeric signals can be plotted; enumerated signals remain visible in frame
details. See [docs/DBC.md](docs/DBC.md).

## Capture, replay and listen-only mode

CSV recording writes arrival time, optional device timestamp, direction, ID, DLC, period,
description, data and raw protocol line. Replay reads valid RX/TX/AUTO rows and schedules TX
using capture timestamps.

**Replay, manual TX and automatic responses can actuate connected equipment.** OCA requests
confirmation before replay, starts with listen-only selected and blocks TX while listen-only
is active. Actual electrical passivity depends on compatible protocol v2 hardware confirming
`LISTEN` mode. Read [docs/SAFETY.md](docs/SAFETY.md) before transmitting.

## Language and configuration

Automatic language mode selects Portuguese for `pt-BR` and `pt-PT` operating-system locales;
all other locales use English. Choose Automatic, English or Brazilian Portuguese in the top
bar. The new language is applied after restart so serial capture state is never rebuilt while
running. Missing translations fall back to English.

Normal configuration is stored in the user's platform-specific configuration directory. Set
`OCA_PORTABLE=1` or create a `.portable` file beside the executable to keep `config.json` beside
the application. Runtime configuration, captures and private DBC files are ignored by Git.

## Tests and standalone builds

```bash
python tools/validate_project.py
python -m unittest discover -s tests -v
python -m pip install -r requirements-dev.txt
python tools/build_package.py
```

The build is created under `dist/OpenCANAnalyzer`. Platform-specific instructions are in
[docs/BUILDING.md](docs/BUILDING.md). GitHub Actions tests Python 3.9 and 3.12 and builds on
Windows, Ubuntu and macOS.

## Current limitations

- Standard 11-bit Classical CAN only; no extended IDs, RTR or CAN FD.
- One serial channel at a time.
- Protocol v1 cannot enforce or report hardware listen-only mode.
- Replay timing uses the desktop scheduler and is not deterministic real time.
- USB/OS scheduling affects arrival timestamps when device timestamps are unavailable.
- DBC multiplexing and decoding depend on `cantools` behavior and the selected database.
- OCA is alpha software and has not been certified for production or safety-critical use.

## Roadmap

- Extended-ID, RTR and CAN FD protocol evolution.
- Multiple transport and channel support.
- Improved offline capture analysis and replay controls.
- More complete profile editor and JSON schema.
- Signed, reproducible release packages.
- Additional community translations.

## Contributing and license

Read [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md),
[SECURITY.md](SECURITY.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Sanitize captures
and never submit proprietary DBC data. Open CAN Analyzer is released under the [MIT License](LICENSE).
