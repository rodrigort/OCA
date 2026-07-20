# OCA Serial Protocol

The transport is ASCII text over USB CDC. Every command or response ends with CR/LF
or LF. Hexadecimal CAN IDs and bytes are uppercase in generated output.

## Negotiation

Host request:

```text
HELLO?
```

Example device response:

```text
HELLO,2,OCA-Compatible-Device,1.0.0
```

If the device does not answer with `HELLO`, the host remains in protocol v1 mode.

## Receive frames

Legacy v1:

```text
RX,<id>,<dlc>,<b0>,<b1>,<b2>,<b3>,<b4>,<b5>,<b6>,<b7>
```

Version 2:

```text
RX2,<timestamp_ms>,<id>,<dlc>,<b0>,<b1>,<b2>,<b3>,<b4>,<b5>,<b6>,<b7>
```

Eight byte fields are always present. Only the first `dlc` fields belong to the CAN payload.

## Transmit frames

Legacy v1:

```text
TX,<id>,<dlc>,<b0>,<b1>,<b2>,<b3>,<b4>,<b5>,<b6>,<b7>
```

Version 2:

```text
TX2,<sequence>,<id>,<dlc>,<b0>,<b1>,<b2>,<b3>,<b4>,<b5>,<b6>,<b7>
```

Successful bus transmission is confirmed after the CAN TX event:

```text
OK,TX,<sequence>,<id>
```

An accepted transmit request is not itself treated as bus confirmation.

## Controller diagnostics

Host request:

```text
GET,STATUS
```

Response:

```text
STATUS,<rx>,<tx>,<queue_dropped>,<message_lost>,<state>,<tec>,<rec>,<mode>
```

States are `OK`, `ERROR_WARNING`, `ERROR_PASSIVE` or `BUS_OFF`.
Mode is `ACTIVE` or `LISTEN`. The host changes it with `SET,LISTEN,1` or
`SET,LISTEN,0`; firmware answers `OK,LISTEN,1|0`.

## Errors

- `ERR,CMD`: malformed or unsupported command.
- `ERR,DLC`: DLC outside 0..8.
- `ERR,ID`: standard ID outside 0x000..0x7FF.
- `ERR,SEQ`: invalid v2 sequence.
- `ERR,CAN[,sequence]`: CAN transmit object/controller busy.

A compatible implementation should abort an unconfirmed TX request within a documented,
bounded interval and report `ERR,CAN`. This prevents a disconnected or unterminated bus from
blocking later commands forever.

## Compatibility and safety requirements

- Parsers must reject IDs above `0x7FF`, DLC above 8 and bytes above `0xFF`.
- A device must not report `OK,TX` before the controller confirms the actual bus TX event.
- `LISTEN` must configure the CAN controller for hardware listen-only operation; merely
  suppressing host commands is insufficient.
- Unknown commands should return `ERR,CMD` without changing mode or transmitting.
- Version 2 devices should continue accepting v1 `TX` commands unless explicitly documented.
