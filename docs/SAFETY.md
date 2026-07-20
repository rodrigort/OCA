# CAN Safety

## Before connecting

- Work on an isolated bench network whenever possible.
- Verify authorization, voltage levels, CAN bitrate, transceiver compatibility, common
  reference, termination and protection.
- Start with listen-only selected and confirm the device reports `LISTEN`.
- Capture and identify normal traffic before considering transmission.

## Transmission and automatic responses

One CAN frame can change actuator, power or controller state. Validate ID, DLC and every byte.
Keep automatic responses disabled until the rules have been reviewed. Do not use desktop
automatic responses for deterministic control, interlocks or emergency functions.

## Replay

Replay can reproduce commands outside their original system state and timing. OCA asks for
confirmation, but cannot determine whether a frame is safe. Inspect and sanitize the CSV,
disconnect actuators where appropriate, provide an emergency stop and supervise the bench.

## Listen-only limitations

The UI checkbox blocks OCA TX locally. Electrical passivity requires protocol v2 hardware to
place its CAN controller in true listen-only mode and confirm it. Protocol v1 cannot provide
that assurance. Bus errors, acknowledgements and transceiver behavior are hardware concerns.

OCA is not certified for public-road, medical, rail, aerospace, industrial safety or other
safety-critical operation.
