# Changelog

All notable changes are documented here. OCA follows Semantic Versioning.

## [0.4.0] - 2026-07-20

- Prepared the desktop application as a self-contained public repository.
- Added English and Brazilian Portuguese catalogs, OS-language detection, manual selection,
  persistence and English fallback.
- Replaced the fixed serial-port default with discovery and cross-platform port handling.
- Added user and portable configuration paths suitable for source and frozen builds.
- Added public CSV, DBC and profile examples without real bus data.
- Strengthened profile, protocol and capture validation and expanded automated tests.
- Added Windows, Linux and macOS CI and PyInstaller builds.
- Added complete community, security, architecture, profile, DBC, build and safety documentation.
- Improved macOS dark-theme colors, widened serial-port selection and screen-aware window sizing.
- Added an official-source Windows driver guide for the XMC4700 Relax Kit on-board J-Link probe.

## [0.3.0] - 2026-07-20

- Replaced the basic B0 plot with a timestamped trend panel for B0-B7 and numeric DBC signals.
- Added automatic ID selection, time-window control and adaptive or fixed vertical scale.
- Added pause/resume, per-ID history clearing and live current/minimum/maximum statistics.
- Added a local graph demo that never transmits CAN frames.
- Retained up to 5,000 frames per ID with bounded redraw frequency and visual downsampling.
- Added automated tests for DBC signal discovery and numeric decoding.

## [0.2.0] - 2026-07-20

- Renamed the desktop product to Open CAN Analyzer (OCA).
- Added protocol v2 negotiation while preserving protocol v1 compatibility.
- Added MCU timestamps, RX drop counters and CAN controller diagnostics.
- Added TX sequence numbers and event-based TX confirmation.
- Increased the firmware RX queue from 8 to 32 frames.
- Added bounded desktop processing for high traffic loads.
- Added latest-frame-per-ID view, direction filters, DBC decoding and CSV replay.
- Added hardware listen-only mode, candump export, profile editor and basic B0 history plot.
- Added automated protocol/profile tests and open-source project files.

## [0.1.0]

- Initial USB serial CAN RX/TX bridge and Tkinter desktop analyzer.
