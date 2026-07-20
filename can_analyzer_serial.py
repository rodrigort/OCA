#!/usr/bin/env python3
"""Portable terminal console for Open CAN Analyzer compatible devices."""

import argparse
import csv
import datetime as dt
import sys
import threading
import time

from oca.config import load_config, resource_path
from oca.i18n import Translator
from oca.protocol import ProtocolError, parse_line

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None


tr = Translator(resource_path("locales"), load_config().get("language", "auto"))


def parse_args():
    global tr
    language_probe = argparse.ArgumentParser(add_help=False)
    language_probe.add_argument("--language", choices=("auto", "en", "pt_BR"))
    selected, _unknown = language_probe.parse_known_args()
    if selected.language:
        tr = Translator(resource_path("locales"), selected.language)
    parser = argparse.ArgumentParser(description=tr("terminal.description"))
    parser.add_argument("--port", help=tr("terminal.port_help"))
    parser.add_argument("--baud", type=int, default=115200, help=tr("terminal.baud_help"))
    parser.add_argument("--csv", help=tr("terminal.csv_help"))
    parser.add_argument("--list", action="store_true", help=tr("terminal.list_help"))
    parser.add_argument("--language", choices=("auto", "en", "pt_BR"), help=tr("terminal.language_help"))
    return parser.parse_args()


def normalize_port_name(port):
    port = port.strip()
    if port.upper().startswith("COM"):
        return port.upper()
    return port


def format_rx_line(line):
    try:
        message = parse_line(line)
    except ProtocolError:
        return line.strip()
    if message.kind != "FRAME":
        return line.strip()
    frame = message.frame
    data_text = " ".join(f"{byte:02X}" for byte in frame.data)
    stamp = f" T={frame.timestamp_ms} ms" if frame.timestamp_ms is not None else ""
    return f"[RX]{stamp} ID=0x{frame.can_id:03X} DLC={frame.dlc} DATA={data_text}"


def build_tx_command(text):
    text = text.strip()
    if not text:
        return None
    if text.upper().startswith("TX,"):
        return text + "\n"

    parts = text.replace(",", " ").split()
    if len(parts) < 2:
        raise ValueError(tr("terminal.tx_usage"))

    can_id = int(parts[0], 16)
    dlc = int(parts[1], 0)
    data = [int(item, 16) for item in parts[2:]]
    while len(data) < 8:
        data.append(0)
    if can_id > 0x7FF:
        raise ValueError(tr("terminal.id_error"))
    if not 0 <= dlc <= 8:
        raise ValueError(tr("terminal.dlc_error"))
    if len(data) > 8 or any(byte > 0xFF or byte < 0 for byte in data):
        raise ValueError(tr("terminal.data_error"))

    data_text = ",".join(f"{byte:02X}" for byte in data[:8])
    print(f"[TX] ID=0x{can_id:03X} DLC={dlc} DATA={' '.join(f'{byte:02X}' for byte in data[:8])}")
    return f"TX,{can_id:03X},{dlc},{data_text}\n"


def print_serial_ports():
    if list_ports is None:
        print(tr("terminal.no_pyserial"))
        return

    ports = list(list_ports.comports())
    if not ports:
        print(tr("terminal.no_ports"))
        return

    for port in ports:
        print(f"{port.device}: {port.description}")


def get_serial_port_names():
    if list_ports is None:
        return []
    return [port.device.upper() for port in list_ports.comports()]


def reader_thread(ser, stop_event, csv_writer, csv_file, print_lock):
    while not stop_event.is_set():
        try:
            raw = ser.readline()
        except serial.SerialException as exc:
            with print_lock:
                print(f"\n{tr('terminal.read_error', error=exc)}")
            stop_event.set()
            break

        if not raw:
            continue

        line = raw.decode("ascii", errors="replace").strip()
        with print_lock:
            print(f"\r{format_rx_line(line)}")
            print("> ", end="", flush=True)

        if csv_writer and (line.startswith("RX,") or line.startswith("RX2,")):
            try:
                frame = parse_line(line).frame
                csv_writer.writerow([
                    dt.datetime.now().isoformat(timespec="milliseconds"),
                    "RX", f"0x{frame.can_id:03X}", frame.dlc, frame.timestamp_ms,
                    " ".join(f"{byte:02X}" for byte in frame.data), line,
                ])
            except ProtocolError:
                pass
            if csv_file:
                csv_file.flush()


def main():
    global tr
    args = parse_args()

    if args.list:
        print_serial_ports()
        return 0 if list_ports is not None else 2

    if not args.port:
        print(tr("terminal.port_required"))
        print_serial_ports()
        return 2

    if serial is None:
        print(tr("terminal.no_pyserial"))
        return 2

    args.port = normalize_port_name(args.port)
    detected_ports = get_serial_port_names()
    if detected_ports and args.port.upper() not in detected_ports:
        print(tr("terminal.port_warning", port=args.port))
        print(tr("terminal.port_required"))
        print_serial_ports()
        print(tr("terminal.try_anyway"))

    stop_event = threading.Event()
    print_lock = threading.Lock()

    try:
        csv_file = open(args.csv, "a", newline="", encoding="utf-8") if args.csv else None
    except OSError as exc:
        print(tr("terminal.csv_failed", path=args.csv, error=exc))
        return 2

    csv_writer = csv.writer(csv_file) if csv_file else None
    if csv_writer and csv_file.tell() == 0:
        csv_writer.writerow(["timestamp", "type", "id", "dlc", "device_timestamp_ms", "data", "raw"])

    try:
        ser = serial.Serial(args.port, args.baud, timeout=0.1)
    except serial.SerialException as exc:
        print(tr("terminal.open_failed", port=args.port, error=exc))
        print(tr("terminal.checks"))
        if csv_file:
            csv_file.close()
        return 2
    except OSError as exc:
        print(tr("terminal.os_open_error", port=args.port, error=exc))
        if csv_file:
            csv_file.close()
        return 2

    with ser:
        thread = threading.Thread(
            target=reader_thread,
            args=(ser, stop_event, csv_writer, csv_file, print_lock),
            daemon=True,
        )
        thread.start()
        print(tr("terminal.opened", port=args.port))

        try:
            while not stop_event.is_set():
                with print_lock:
                    text = input("> ")
                try:
                    command = build_tx_command(text)
                    if command:
                        ser.write(command.encode("ascii"))
                except ValueError as exc:
                    with print_lock:
                        print(tr("terminal.error", error=exc))
        except (KeyboardInterrupt, EOFError):
            stop_event.set()
        finally:
            time.sleep(0.1)
            if csv_file:
                csv_file.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
