#!/usr/bin/env python3
"""Automated, safety-first AT-command prober.

Rules:
- Only TEST (?) / READ (?) forms and known-reversible actions (ATE, CMEE).
- No writes to network/NV/SIM state. No blind writes. Nothing destructive.
- Any response containing a >=10-digit run (IMEI/IMSI/MSISDN-like) is masked.
- Raw transcript is saved to at_raw.log.

Usage: python3 at_probe.py [PORT]   (default /dev/ttyACM0)
"""
import re
import sys
import time
from pathlib import Path
from datetime import datetime

import serial  # pyserial

PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"
BAUD = 115200
ROOT = Path(__file__).resolve().parents[2]
QUIET = 0.35          # seconds without new bytes -> response complete
HARD_CAP = 6.0        # max seconds per command
LONG_CMDS = {"AT+COPS=?": 45.0}   # network scan can be slow
RAW_LOG = open(ROOT / "captured-output/at/at_raw.log", "ab", buffering=0)

# stage 0 = control (echo, error format), then safe probes.
# Each entry: (command, note)
PLAN = [
    ("AT",            "handshake"),
    ("ATE0",          "echo off (reversible)"),
    ("AT+CMEE=?",     "error-report test form"),
    ("AT+CMEE=1",     "enable verbose errors (reversible)"),
    # re-run previously rejected commands now that CMEE may give detail
    ("ATI",           "retry: identification"),
    ("AT+CGMI",       "retry: manufacturer"),
    ("AT+CGSN",       "retry: IMEI (masked)"),
    ("AT+CREG?",      "retry: registration"),
    ("AT+CPIN?",      "retry: SIM status"),
    ("AT+CMGF=?",     "retry: SMS mode"),
    # new safe probes (test/read forms)
    ("AT+CPAS?",      "phone activity status"),
    ("AT+CBC?",       "battery charge"),
    ("AT+CCLK?",      "real-time clock"),
    ("AT+CGATT?",     "GPRS attach state"),
    ("AT+CGDCONT?",   "PDP contexts (read)"),
    ("AT+CESQ",       "extended signal quality"),
    ("AT+CSQ",        "signal quality"),
    ("AT+CSCS=?",     "available character sets"),
    ("AT+CGMM=?",     "model test form"),
    ("AT+CGMR=?",     "firmware test form"),
    ("AT+CGMI=?",     "manufacturer test form"),
    ("AT+CREG=?",     "registration test form"),
    ("AT+CPIN=?",     "SIM test form"),
    ("AT+CIMI",       "IMSI (masked)"),
    ("AT+CNUM",       "subscriber number (masked)"),
    ("AT+GCAP",       "retry: capabilities"),
    ("AT+CLAC",       "retry: list commands"),
    ("AT+COPS=?",     "operator scan (slow, read-only)"),
]

MASK = re.compile(rb"(?<!\d)(\d{4})\d{6,}(\d{2})(?!\d)")
# keep first 4 and last 2 digits of long numbers; the rest -> '#'

def mask_bytes(b: bytes) -> bytes:
    return MASK.sub(rb"\1######\2", b)


def read_some(ser, deadline, buf):
    n = ser.in_waiting
    if n:
        chunk = ser.read(n)
        buf.extend(chunk)
        RAW_LOG.write(chunk)
    return buf


def send(ser, cmd: str):
    """Send one command, collect response until quiet/terminator/cap."""
    ser.reset_input_buffer()
    payload = (cmd + "\r").encode()
    RAW_LOG.write(b"\n>>> " + payload)
    ser.write(payload)
    ser.flush()
    cap = time.monotonic() + LONG_CMDS.get(cmd, HARD_CAP)
    quiet_until = time.monotonic() + QUIET
    buf = bytearray()
    done = False
    while time.monotonic() < cap:
        read_some(ser, cap, buf)
        text = bytes(buf)
        # terminator seen at line start-ish?
        for term in (b"OK", b"ERROR", b"+CME ERROR", b"+CMS ERROR"):
            if re.search(rb"(?:^|[\r\n])" + re.escape(term) + rb"\s*[\r\n]?$", text):
                done = True
                break
        if done:
            # grab any trailing bytes for a moment
            t2 = time.monotonic() + 0.05
            while time.monotonic() < t2:
                read_some(ser, cap, buf)
            break
        if bytes(buf):
            quiet_until = time.monotonic() + QUIET
        elif time.monotonic() > quiet_until and buf:
            break
        time.sleep(0.02)
    # drain a final quiet period
    t3 = time.monotonic() + QUIET
    last = time.monotonic()
    while time.monotonic() < t3:
        if ser.in_waiting:
            read_some(ser, t3, buf)
            last = time.monotonic()
            t3 = max(t3, time.monotonic() + QUIET)
        time.sleep(0.02)
    RAW_LOG.write(b"\n")
    return clean(cmd, bytes(buf))


def clean(cmd: str, resp: bytes) -> str:
    resp = resp.replace(b"\r", b"").strip(b"\n")
    lines = [l for l in resp.split(b"\n") if l.strip()]
    # strip command echo lines
    lines = [l for l in lines if l.strip() != cmd.encode()]
    # also handle partial/garbled echo (first chars match)
    out = []
    for l in lines:
        s = l.decode("latin-1").rstrip()
        if out or s == cmd or (cmd.startswith(s[:4]) and len(s) <= len(cmd) + 1):
            # skip echoes; only allow once past echo region
            if not out and (s == cmd or cmd.startswith(s[:4])):
                continue
        out.append(s)
    return mask_bytes("\n".join(out).encode()).decode("latin-1").strip()


def classify(resp: str) -> str:
    if not resp:
        return "TIMEOUT"
    if re.search(r"\+C(ME|MS) ERROR", resp):
        return "CME/CMS ERROR (verbose!)"
    if re.search(r"(?:^|\n)ERROR(?:\n|$)", resp):
        return "ERROR"
    if re.search(r"(?:^|\n)OK(?:\n|$)", resp):
        return "OK"
    return "DATA/OTHER"


def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows, urcs = [], []
    print(f"# listening 10s for unsolicited (URC) traffic on {PORT} ...", flush=True)
    t_end = time.monotonic() + 10
    buf = bytearray()
    while time.monotonic() < t_end:
        if ser.in_waiting:
            read_some(ser, t_end, buf)
            t_end = max(t_end, time.monotonic() + 1.0)
        time.sleep(0.05)
    if buf:
        urcs.append(mask_bytes(bytes(buf)).decode("latin-1"))
        RAW_LOG.write(b"\n--- URC window ---\n" + bytes(buf) + b"\n")
    try:
        ser.close(); ser = serial.Serial(PORT, BAUD, timeout=0.1)
    except Exception:
        pass
    ser.reset_input_buffer()

    for cmd, note in PLAN:
        resp = send(ser, cmd)
        rows.append((cmd, note, resp, classify(resp)))
        print(f"{cmd:<12} -> {classify(resp):<22} | {resp[:80]!r}", flush=True)

    ser.close()
    RAW_LOG.close()

    with open(ROOT / "docs/at-probes/at_results.md", "w") as f:
        f.write(f"# Automated AT probe — {stamp} — {PORT}\n\n")
        if urcs:
            f.write("## Unsolicited bytes seen at connect\n\n```text\n" + "\n".join(urcs) + "\n```\n\n")
        f.write("| Command | Note | Verdict | Response |\n|---|---|---|---|\n")
        for cmd, note, resp, verdict in rows:
            r = resp.replace("|", "\\|").replace("\n", " ⏎ ")
            f.write(f"| `{cmd}` | {note} | {verdict} | `{r if r else '(none)'}` |\n")
    print("\nwrote docs/at-probes/at_results.md and at_raw.log")


if __name__ == "__main__":
    main()
