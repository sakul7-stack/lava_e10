#!/usr/bin/env python3
"""Phase-3 probe: indicator names, URC window, audio/DTMF test forms.
Read/test forms only; CMER is enabled then disabled (reversible).
Saves at_results3.md; raw bytes to at_raw.log."""
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
    ("AT",          "handshake"),
    ("ATE0",        "echo off"),
    ("AT+CMEE=1",   "verbose errors"),
    ("AT+CIND=?",   "enumerate indicator names"),
    ("AT+CLCC=?",   "list-calls test form"),
    ("AT+VTD=?",    "DTMF duration test form"),
    ("AT+VTS=?",    "DTMF test form"),
    ("AT+CALM?",    "alert tone mode (read)"),
    ("AT+CLVL?",    "loudspeaker volume (read)"),
    ("AT+CVOICE=?", "voice mode test form"),
    ("AT+CTZU=?",   "timezone update test form"),
    ("AT+CTZR=?",   "timezone reporting test form"),
    ("AT+CPOL?",    "preferred operator list (read)"),
    ("AT+CMER=3,0,0,1", "enable indicator URCs (reversible)"),
]

MASK = re.compile(rb"(?<!\d)(\d{4})\d{6,}(\d{2})(?!\d)")


def read_some(ser, buf):
    n = ser.in_waiting
    if n:
        chunk = ser.read(n)
        buf.extend(chunk)
        RAW_LOG.write(chunk)


def send(ser, cmd, cap_s=HARD_CAP):
    ser.reset_input_buffer()
    payload = (cmd + "\r").encode()
    RAW_LOG.write(b"\n>>> " + payload)
    ser.write(payload)
    ser.flush()
    cap = time.monotonic() + cap_s
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
    while time.monotonic() < t3:
        if ser.in_waiting:
            read_some(ser, buf)
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
        print(f"{cmd:<18} -> {classify(resp):<14} | {resp[:100]!r}", flush=True)

    # 20-second URC window with indicator reporting enabled
    print("\n# listening 20s for URCs (CMER on) ...", flush=True)
    buf = bytearray()
    t_end = time.monotonic() + 20
    while time.monotonic() < t_end:
        read_some(ser, buf)
        time.sleep(0.05)
    urc = clean("(urc window)", bytes(buf))
    print(f"URC window: {urc!r}", flush=True)

    # restore: indicators off, charsets verified
    for cmd in ("AT+CMER=0,0,0,0", "AT+CSCS?"):
        resp = send(ser, cmd)
        rows.append((cmd, "restore state", resp, classify(resp)))
        print(f"{cmd:<18} -> {classify(resp):<14} | {resp[:60]!r}", flush=True)

    ser.close()
    RAW_LOG.close()

    with open(ROOT / "docs/at-probes/at_results3.md", "w") as f:
        f.write(f"# AT probe phase 3 — {datetime.now():%Y-%m-%d %H:%M:%S} — {PORT}\n\n")
        if urc:
            f.write("URC window (20 s, CMER on):\n\n```text\n" + urc + "\n```\n\n")
        f.write("| Command | Note | Verdict | Response |\n|---|---|---|---|\n")
        for cmd, note, resp, verdict in rows:
            r = resp.replace("|", "\\|").replace("\n", " ⏎ ")
            f.write(f"| `{cmd}` | {note} | {verdict} | `{r if r else '(none)'}` |\n")
    print("\nwrote docs/at-probes/at_results3.md")


if __name__ == "__main__":
    main()
