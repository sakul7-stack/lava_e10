#!/usr/bin/env python3
"""Deliberate AT write-form SMS attempt (user-authorized test number).

Rationale: all previous probes only used TEST forms (AT+CMGF=?, AT+CMGS=?).
Some MTK builds expose write handlers even when test handlers return
CME ERROR 100. This script tries the real write forms:

  AT+CMGF=1            (text mode - standard 27.005, reversible)
  AT+CMGS="<number>"   then wait for the '>' prompt, send text + Ctrl-Z

Safety:
- Number is supplied through SMS_TEST_NUMBER and masked in all output.
- If nothing answers within the timeout, an ESC is sent to cancel any
  half-open SMS composition, then ATH is sent as a belt-and-braces restore.
- No other writes are attempted. Raw log scrubbed of long digit runs.

Usage: python3 sms_at_attempt.py [PORT]
"""
import os
import re
import sys
import time
from pathlib import Path
from datetime import datetime

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"
BAUD = 115200
ROOT = Path(__file__).resolve().parents[2]
NUMBER = os.environ.get("SMS_TEST_NUMBER", "")
TEXT = "HELLO FROM LAVA E10 USB AT TEST"
RAW_LOG = open(ROOT / "captured-output/sms/sms_at_attempt.log", "wb", buffering=0)
MASK = re.compile(rb"(?<!\d)(\d{4})\d{6,}(\d{2})(?!\d)")


def masked(b):
    return MASK.sub(rb"\1######\2", b)


def read_for(ser, seconds):
    buf = bytearray()
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        n = ser.in_waiting
        if n:
            chunk = ser.read(n)
            buf.extend(chunk)
            RAW_LOG.write(chunk)
        else:
            time.sleep(0.02)
    return bytes(buf)


def send_expect(ser, cmd, expect, timeout):
    ser.reset_input_buffer()
    payload = (cmd + "\r").encode()
    RAW_LOG.write(b"\n>>> " + payload)
    ser.write(payload)
    ser.flush()
    resp = read_for(ser, timeout)
    ok = expect in resp
    out = masked(resp).replace(b"\r", b"").decode("latin-1").strip()
    print(f"  {cmd[:40]:<40} -> {out!r}  [{'MATCH' if ok else 'no-match'}]",
          flush=True)
    return resp, ok


def main():
    if not re.fullmatch(r"\+[0-9]{6,15}", NUMBER):
        sys.exit("set SMS_TEST_NUMBER to a +country-code phone number")
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    print(f"AT write-form SMS attempt — {datetime.now():%Y-%m-%d %H:%M:%S}",
          flush=True)
    try:
        send_expect(ser, "AT", b"OK", 2)
        send_expect(ser, "ATE0", b"OK", 2)
        send_expect(ser, "AT+CMEE=1", b"OK", 2)

        # 1) text mode - the write form never tried before
        resp, ok = send_expect(ser, "AT+CMGF=1", b"OK", 4)
        if not ok:
            print("  => CMGF=1 rejected: AT-level SMS confirmed dead "
                  "(write handler absent too).", flush=True)
            return

        # 2) send form: number variant first
        resp, got_prompt = send_expect(ser, f'AT+CMGS="{NUMBER}"', b">", 6)
        if not got_prompt:
            # 3) PDU-style length variant
            resp, got_prompt = send_expect(ser, "AT+CMGS=30", b">", 6)
        if not got_prompt:
            print("  => CMGS accepted neither form; no prompt.", flush=True)
            return

        # 4) prompt received: compose and transmit
        print("  >>> prompt '>' received - sending body + Ctrl-Z", flush=True)
        payload = (TEXT + "\x1a").encode()
        RAW_LOG.write(b"\n>>> [BODY+CTRL-Z]\n" + masked(payload))
        ser.write(payload)
        ser.flush()
        resp = read_for(ser, 25)
        out = masked(resp).replace(b"\r", b"").decode("latin-1").strip()
        print(f"  final response: {out!r}", flush=True)
        if "+CMGS" in resp:
            print("  *** SMS TRANSMITTED over AT! (+CMGS ack received) ***",
                  flush=True)
        elif re.search(rb"\+CM[E]?S? ERROR", resp) or b"ERROR" in resp:
            print("  => transmission refused by firmware.", flush=True)
        else:
            print("  => ambiguous/timeout - cancelling with ESC.", flush=True)
            ser.write(b"\x1b")
            ser.flush()
            read_for(ser, 3)
    finally:
        # belt-and-braces restore
        ser.write(b"\x1b")
        ser.flush()
        time.sleep(0.5)
        send_expect(ser, "ATH", b"OK", 3)
        ser.close()
        RAW_LOG.close()
        # scrub identifiers from raw log
        p = ROOT / "captured-output/sms/sms_at_attempt.log"
        data = open(p, "rb").read()
        open(p, "wb").write(MASK.sub(rb"\1######\2", data))
        print("raw log scrubbed", flush=True)


if __name__ == "__main__":
    main()
