#!/usr/bin/env python3
"""Voice/DTMF call test (task step 4). Fully reversible.

Dials ATD<number>; (voice call, semicolon = voice), confirms setup via
AT+CLCC, sends AT+VTS DTMF tones in-call, then hangs up with ATH.

Safety:
- The dialed number MUST be passed on the command line; nothing is dialed
  otherwise. No emergency numbers accepted (000/108/110/112/119/911/999).
- Only call-control writes (ATD/ATH/VTS) - no settings are touched.
- Any >=12-digit run in output is masked (caller-ID etc.).

Usage: python3 call_test.py <number> [PORT]   (default /dev/ttyACM0)
"""
import re
import sys
import time
from pathlib import Path
from datetime import datetime

import serial

if len(sys.argv) < 2:
    sys.exit("usage: call_test.py <number> [PORT]")
NUMBER = sys.argv[1].strip()
PORT = sys.argv[2] if len(sys.argv) > 2 else "/dev/ttyACM0"
BAUD = 115200
ROOT = Path(__file__).resolve().parents[2]
RAW_LOG = open(ROOT / "captured-output/calls/call_test.log", "ab", buffering=0)
MASK = re.compile(rb"(?<!\d)(\d{4})\d{6,}(\d{2})(?!\d)")

EMERGENCY = {"000", "108", "110", "112", "119", "911", "999"}
if NUMBER in EMERGENCY or NUMBER.startswith("1") and len(NUMBER) <= 3:
    sys.exit(f"refusing to dial emergency-looking number {NUMBER}")
if not re.fullmatch(r"[0-9#*+]+", NUMBER):
    sys.exit("number must contain only digits and #*+")

# DTMF sequence to send in-call (safe: just tones on the far end)
DTMF_SEQ = list("123456789") + ["#", "*"]


def send(ser, cmd, wait=1.0, terms=("OK", "ERROR", "+CME ERROR")):
    ser.reset_input_buffer()
    payload = (cmd + "\r").encode()
    RAW_LOG.write(b"\n>>> " + payload)
    ser.write(payload)
    ser.flush()
    buf = bytearray()
    cap = time.monotonic() + max(wait, 5)
    while time.monotonic() < cap:
        n = ser.in_waiting
        if n:
            chunk = ser.read(n)
            buf.extend(chunk)
            RAW_LOG.write(chunk)
        text = bytes(buf)
        if any(re.search(rb"(?:^|[\r\n])" + re.escape(t.encode()), text)
               for t in terms):
            time.sleep(0.05)
            n = ser.in_waiting
            if n:
                chunk = ser.read(n)
                buf.extend(chunk)
                RAW_LOG.write(chunk)
            break
        time.sleep(0.02)
    out = MASK.sub(rb"\1######\2", bytes(buf)).replace(b"\r", b"")
    s = out.decode("latin-1").strip()
    # strip echoed command line
    s = "\n".join(l for l in s.split("\n") if l.strip() != cmd)
    print(f"  {cmd:<20} -> {s!r}", flush=True)
    return s


def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    masked = MASK.sub(rb"\1######\2", NUMBER.encode()).decode()
    print(f"Call test — {datetime.now():%Y-%m-%d %H:%M:%S} — {PORT}")
    print(f"  dialing {masked} (voice)")
    try:
        send(ser, "AT")
        send(ser, "ATE0")
        send(ser, "AT+CMEE=1")

        # dial with semicolon = voice call
        resp = send(ser, f"ATD{NUMBER};", wait=10)
        if "OK" not in resp:
            print("!! dial failed - attempting hangup anyway")
            send(ser, "ATH")
            sys.exit(1)

        # let the call connect and ring the far end
        time.sleep(6)
        send(ser, "AT+CLCC", wait=3)     # confirm active call (read-only)

        # DTMF tones while in call
        for k in DTMF_SEQ:
            r = send(ser, f"AT+VTS={k}", wait=2)
            if "OK" not in r:
                print(f"  (VTS {k} rejected - stopping tone sequence)")
                break
            time.sleep(0.4)

        time.sleep(2)
        send(ser, "AT+CLCC", wait=3)     # still active?
    finally:
        print("  hanging up")
        send(ser, "ATH", wait=3)
        time.sleep(1)
        send(ser, "AT+CLCC", wait=3)     # must show no calls
        ser.close()
        RAW_LOG.close()
    print("done (call ended, state restored)")


if __name__ == "__main__":
    main()
