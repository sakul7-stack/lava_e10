#!/usr/bin/env python3
"""Phase-2 probe: follow-ups on /dev/ttyACM0 after CMEE=1 discovery.
Read/test forms only. Saves at_results2.md; raw bytes to at_raw.log."""
import re
import sys
import time
from pathlib import Path
from datetime import datetime

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"
BAUD = 115200
ROOT = Path(__file__).resolve().parents[2]
QUIET = 0.35
HARD_CAP = 6.0
RAW_LOG = open(ROOT / "captured-output/at/at_raw.log", "ab", buffering=0)

PLAN = [
    ("AT",           "handshake"),
    ("ATE0",         "echo off"),
    ("AT+CMEE=1",    "verbose errors on"),
    ("AT+CGMR",      "recheck firmware id"),
    ("AT+CGMM",      "recheck model"),
    ("AT+CFUN?",     "recheck functionality"),
    ("AT+CIND?",     "indicator control (MTK favorite)"),
    ("AT+CMER=?",    "indicator event reporting (test)"),
    ("AT+CR?",       "service reporting"),
    ("AT+CRC?",      "ring type (read)"),
    ("AT+CLCC",      "list current calls (read-only)"),
    ("AT+CSCB?",     "cell broadcast (read)"),
    ("AT+CSCA=?",    "service center (test form)"),
    ("AT+CPMS=?",    "message storage (test form)"),
    ("AT+CMGF?",     "SMS mode (read form)"),
    ("AT+CMUX=?",    "27.010 multiplexer (test) — could give more channels"),
    ("AT+CGREG?",    "GPRS registration (read)"),
    ("AT+CGPADDR",   "PDP address (read)"),
    ("AT+CGEREP=?",  "URC reporting (test)"),
    ("AT+CLIP=?",    "calling line id (test)"),
    ("AT+CHLD=?",    "call hold (test)"),
    ("AT+CVHU=?",    "voice hangup (test)"),
    ("AT+CSQ",       "signal again"),
    ("AT+COPS?",     "operator mode"),
    ("AT+CSCS?",     "current charset"),
]

MASK = re.compile(rb"(?<!\d)(\d{4})\d{6,}(\d{2})(?!\d)")


def read_some(ser, buf):
    n = ser.in_waiting
    if n:
        chunk = ser.read(n)
        buf.extend(chunk)
        RAW_LOG.write(chunk)


def send(ser, cmd):
    ser.reset_input_buffer()
    payload = (cmd + "\r").encode()
    RAW_LOG.write(b"\n>>> " + payload)
    ser.write(payload)
    ser.flush()
    cap = time.monotonic() + HARD_CAP
    buf = bytearray()
    while time.monotonic() < cap:
        read_some(ser, buf)
        text = bytes(buf)
        for term in (b"OK", b"ERROR", b"+CME ERROR", b"+CMS ERROR"):
            if re.search(rb"(?:^|[\r\n])" + re.escape(term), text):
                time.sleep(0.05)
                read_some(ser, buf)
                break
        else:
            time.sleep(0.02)
            continue
        break
    t3 = time.monotonic() + QUIET
    last = time.monotonic()
    while time.monotonic() < t3:
        if ser.in_waiting:
            read_some(ser, buf)
            last = time.monotonic()
            t3 = max(t3, time.monotonic() + QUIET)
        time.sleep(0.02)
    return clean(cmd, bytes(buf))


def clean(cmd, resp):
    resp = resp.replace(b"\r", b"").strip(b"\n")
    lines = [l for l in resp.split(b"\n") if l.strip()]
    lines = [l for l in lines if l.strip() != cmd.encode()]
    out = "\n".join(l.decode("latin-1").rstrip() for l in lines)
    return MASK.sub(rb"\1######\2", out.encode()).decode("latin-1").strip()


def classify(resp):
    if not resp:
        return "TIMEOUT"
    if re.search(r"\+C(ME|MS) ERROR", resp):
        return "CME/CMS ERROR"
    if re.search(r"(?:^|\n)ERROR(?:\n|$)", resp):
        return "ERROR"
    if re.search(r"(?:^|\n)OK(?:\n|$)", resp):
        return "OK"
    return "DATA/OTHER"


def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    rows = []
    for cmd, note in PLAN:
        resp = send(ser, cmd)
        rows.append((cmd, note, resp, classify(resp)))
        print(f"{cmd:<12} -> {classify(resp):<14} | {resp[:90]!r}", flush=True)
    ser.close()
    RAW_LOG.close()

    with open(ROOT / "docs/at-probes/at_results2.md", "w") as f:
        f.write(f"# AT probe phase 2 — {datetime.now():%Y-%m-%d %H:%M:%S} — {PORT}\n\n")
        f.write("| Command | Note | Verdict | Response |\n|---|---|---|---|\n")
        for cmd, note, resp, verdict in rows:
            r = resp.replace("|", "\\|").replace("\n", " ⏎ ")
            f.write(f"| `{cmd}` | {note} | {verdict} | `{r if r else '(none)'}` |\n")
    print("\nwrote docs/at-probes/at_results2.md")


if __name__ == "__main__":
    main()
