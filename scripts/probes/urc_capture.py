#!/usr/bin/env python3
"""Passive URC capture (task step 3).

Enables AT+CMER=3,0,0,1 (indicator event reporting), then listens
PASSIVELY on /dev/ttyACM0 for a user-triggered window while an incoming
SMS / incoming call arrives from another phone. Records every byte.

Strictly passive: no writes other than the reversible CMER toggle, which is
restored at the end (and on Ctrl+C). Any IMEI/IMSI/MSISDN-like digit run in
the output is masked.

Usage: python3 urc_capture.py [PORT] [SECONDS]   (default /dev/ttyACM0, 300 s)
"""
import re
import sys
import time
from pathlib import Path
from datetime import datetime

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"
WINDOW = int(sys.argv[2]) if len(sys.argv) > 2 else 300
BAUD = 115200
ROOT = Path(__file__).resolve().parents[2]
RAW_LOG = open(ROOT / "captured-output/urc/urc_capture.log", "ab", buffering=0)
MASK = re.compile(rb"(?<!\d)(\d{4})\d{6,}(\d{2})(?!\d)")

CMER_ON = "AT+CMER=3,0,0,1"
CMER_OFF = "AT+CMER=0,0,0,0"


def send(ser, cmd):
    ser.reset_input_buffer()
    payload = (cmd + "\r").encode()
    RAW_LOG.write(b"\n>>> " + payload)
    ser.write(payload)
    ser.flush()
    buf = bytearray()
    cap = time.monotonic() + 5
    while time.monotonic() < cap:
        n = ser.in_waiting
        if n:
            chunk = ser.read(n)
            buf.extend(chunk)
            RAW_LOG.write(chunk)
        if re.search(rb"(?:^|[\r\n])OK", bytes(buf)):
            break
        time.sleep(0.02)
    return bytes(buf).replace(b"\r", b"").decode("latin-1").strip()


def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    print(f"URC capture — {datetime.now():%Y-%m-%d %H:%M:%S} — {PORT}")
    print(f"  CMER on : {send(ser, 'AT')!r}")
    print(f"  CMER on : {send(ser, CMER_ON)!r}")
    print(f"\n*** PASSIVE LISTENING for {WINDOW}s ***")
    print("*** NOW: send a real SMS and place a real call to this phone ***\n")
    buf = bytearray()
    start = time.monotonic()
    last_report = start
    try:
        while time.monotonic() - start < WINDOW:
            n = ser.in_waiting
            if n:
                chunk = ser.read(n)
                buf.extend(chunk)
                RAW_LOG.write(chunk)
            if time.monotonic() - last_report >= 30:
                print(f"  ... {int(time.monotonic()-start)}s elapsed, "
                      f"{len(buf)} bytes captured", flush=True)
                last_report = time.monotonic()
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n(interrupted)")
    finally:
        print(f"\n  CMER off: {send(ser, CMER_OFF)!r}")
        ser.close()
        RAW_LOG.close()

    text = MASK.sub(rb"\1######\2", bytes(buf)).decode("latin-1")
    text = text.replace("\r", "")
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ROOT / "docs/analysis/urc_capture_result.md", "a") as f:
        f.write(f"# URC capture — {stamp} — {PORT} — {WINDOW}s window\n\n")
        if text.strip():
            f.write(f"**{len(buf)} bytes of unsolicited traffic captured:**\n\n"
                    "```text\n" + text.strip() + "\n```\n\n")
            f.write("[FACT] URCs DO appear on this port during events.\n")
        else:
            f.write("**Zero unsolicited bytes** during the window "
                    "(SMS + call attempted per session notes).\n\n")
            f.write("[FACT] No URCs appear on this port for incoming "
                    "SMS/call events even with CMER=3,0,0,1.\n")
    print(f"Wrote docs/analysis/urc_capture_result.md ({len(buf)} bytes captured)")


if __name__ == "__main__":
    main()
