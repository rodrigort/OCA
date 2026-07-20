# OCA Desktop Architecture

```text
Compatible CAN adapter
  CAN controller/transceiver
          |
  USB serial text protocol
          |
  background reader thread
          |
  bounded receive queue
          |
  protocol parser ------> status / negotiation
          |
  Tkinter event loop ---> tables / graph / DBC / CSV / profiles
```

## Modules

- `oca.protocol`: immutable protocol data and v1/v2 parsing/encoding.
- `oca.serial_ports`: platform-neutral discovery prioritization.
- `oca.profiles`: JSON loading and validation.
- `oca.dbc`: optional `cantools` adapter with graceful absence handling.
- `oca.capture`: sanitized CSV replay reader.
- `oca.i18n`: OS-language selection and JSON catalog fallback.
- `oca.config`: source/frozen resources and user/portable configuration paths.
- `can_analyzer_gui.py`: Tkinter presentation and workflow orchestration.
- `can_analyzer_serial.py`: terminal client for diagnostics and simple TX/RX.

## Concurrency and state

Only the reader thread touches blocking serial reads. It places lines into a queue bounded at
5,000 items. The Tkinter thread processes limited batches, parses frames and updates UI state.
This preserves responsiveness during bursts and prevents Tk calls from a worker thread.
Tables and graph history are bounded. CSV writes happen on the UI thread after parsing.

Language changes are persisted and applied after restart. This avoids rebuilding Tk widgets
while serial capture, replay callbacks or graph history may be active.

## Data boundaries

Protocol and public profile data are repository resources. User configuration and recordings
are runtime data and are not committed. DBC files are loaded only from a user-selected path.
No network service or telemetry is present.

## Extension rules

New transports should feed complete OCA text lines into the same parser. Hardware-specific
IDs belong in external profiles, not the parser or GUI. Real-time control and safety functions
do not belong in desktop auto-response logic. Protocol changes must be documented, tested and
remain compatible or introduce explicit version negotiation.
