# CAN Analyzer firmware for XMC4700 Relax Kit

This directory is a standalone Infineon DAVE 4 project for the
`KIT_XMC47_RELAX_V1`. It bridges the XMC4700 MultiCAN peripheral to a USB CDC
serial connection using the OCA text protocol documented in
[`../../docs/PROTOCOL.md`](../../docs/PROTOCOL.md).

## Tested configuration

- Target: XMC4700-F144x2048, ARM Cortex-M4
- IDE/project format: Infineon DAVE 4
- CAN: Classical CAN, 500 kbit/s, standard 11-bit identifiers
- CAN node: MultiCAN node 1
- CAN TX: P1.12 / CAN.N1_TXD
- CAN RX: P1.13 / CAN.N1_RXDC
- CANH: connector X2, pin 33
- CANL: connector X2, pin 35
- USB transport: USB device CDC through application connector X100
- Debug/programming: on-board J-Link through debug connector X101

The official board manual states that the on-board IFX1051LE CAN interface is
not terminated. Add the correct external 120-ohm termination for the bus
topology and connect a common reference where required.

## Firmware behavior

`main.c` initializes the generated DAVE APPs, CAN analyzer and USB CDC device.
The main loop processes USB commands, forwards queued CAN frames and updates the
status LEDs. CAN events are handled by an interrupt and copied into a bounded
32-frame queue so USB formatting remains outside the interrupt.

The firmware supports:

- OCA protocol v1 and v2 discovery;
- RX frames with millisecond device timestamps;
- standard-ID TX with completion acknowledgement;
- controller status and receive-drop diagnostics;
- hardware listen-only control;
- validation of IDs, DLC and payload bytes;
- LED heartbeat and USB-enumeration indication.

## Import, build and flash

1. Install Infineon DAVE 4 and the required XMC device support.
2. Open a DAVE workspace outside this project directory.
3. Choose **File > Import > General > Existing Projects into Workspace**.
4. Select this `CAN_Analyzer_XMC4700_Relax` directory as the project root.
5. Confirm that the target is `XMC4700_F144x2048`.
6. Generate DAVE code if the IDE requests it.
7. Build the **Debug** configuration.
8. Connect the kit's debug USB connector X101 and flash/debug through the
   on-board J-Link probe.
9. Connect application USB X100 to the host running Open CAN Analyzer.

Build output belongs under `Debug/` or `Release/` and is intentionally excluded
from Git. Windows driver guidance is in
[`../../docs/WINDOWS_DRIVER.md`](../../docs/WINDOWS_DRIVER.md).

## Hardware references

- [Infineon KIT_XMC47_RELAX_V1 product page](https://www.infineon.com/evaluation-board/KIT-XMC47-RELAX-V1)
- [Official XMC4700/XMC4800 Relax Kit Series user manual](https://www.infineon.com/assets/row/public/documents/30/44/infineon-board-user-manual-xmc4700-xmc4800-relax-kit-series-usermanual-en.pdf)

## Safety

Start in listen-only mode on an unknown network. Verify bitrate, pinout,
termination, grounding and voltage levels before enabling transmission. This is
an educational and bench-development project, not a certified automotive or
industrial diagnostic product. Read [`../../docs/SAFETY.md`](../../docs/SAFETY.md).

## Licensing

Original OCA firmware files are covered by the repository MIT license. DAVE
APPs, generated code, XMCLib, CMSIS and USB components retain the copyright and
license notices embedded in their source files. See
[`../../THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md).
