#!/usr/bin/env python3
"""Phase-6 probe: SMS-path completeness sweep (read/test forms only).

Goals:
1. Test-form sweep of EVERY remaining TS 27.005 SMS command not yet probed,
   to formally close the "standard SMS set" question with CMEE=1.
2. A handful of explicitly-labeled MTK vendor SMS guesses (test forms only).
3. Re-verify the CMER 'message' indicator path (reversible) for the future
   SIM-enabled URC test.

Safety: test/read forms ONLY. No writes except the reversible CMER toggle.
Masking enabled. Raw -> at_raw6.log ; results -> at_results6.md.
Usage: python3 at_probe6.py [PORT]
"""
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
RAW_LOG = open(ROOT / "captured-output/at/at_raw6.log", "wb", buffering=0)

MASK = re.compile(rb"(?<!\d)(\d{4})\d{6,}(\d{2})(?!\d)")
PROMPT = re.compile(rb"(?:^|\r\n)>\s*(?:\r\n)?$")


class AbortSession(Exception):
    pass


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
        if PROMPT.search(text):
            raise AbortSession("SMS input prompt observed - aborting")
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


def step(ser, cmd, note, rows):
    resp = send(ser, cmd)
    verdict = classify(resp)
    rows.append((cmd, note, resp, verdict))
    print(f"  {cmd:<16} {verdict:<14} | {resp[:90].replace(chr(10), ' | ')}",
          flush=True)
    return resp, verdict


def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    rows = []
    print(f"Phase-6 SMS sweep — {datetime.now():%Y-%m-%d %H:%M:%S} — {PORT}\n",
          flush=True)
    try:
        step(ser, "AT", "handshake", rows)
        step(ser, "ATE0", "echo off", rows)
        step(ser, "AT+CMEE=1", "verbose errors", rows)
        step(ser, "AT+ESIMS?", "SIM presence recheck", rows)

        # --- TS 27.005 commands not yet test-formed in phases 1-4 ---
        step(ser, "AT+CMGR=?", "SMS read (test)", rows)
        step(ser, "AT+CMGW=?", "SMS write to storage (test)", rows)
        step(ser, "AT+CMGD=?", "SMS delete (test)", rows)
        step(ser, "AT+CMSS=?", "SMS send from storage (test)", rows)
        step(ser, "AT+CNMA=?", "new-message acknowledgement (test)", rows)
        step(ser, "AT+CSMP=?", "SMS text-mode parameters (test)", rows)
        step(ser, "AT+CSCB=?", "cell broadcast types (test)", rows)
        step(ser, "AT+CMGC=?", "SMS command (test)", rows)
        step(ser, "AT+CSMS=?", "message service selection (test)", rows)
        step(ser, "AT+CSAS=?", "save SMS settings (test)", rows)
        step(ser, "AT+CRES=?", "restore SMS settings (test)", rows)
        step(ser, "AT+CPMS?", "preferred message storage (read)", rows)
        step(ser, "AT+CSCA?", "service centre address (read)", rows)

        # --- MTK vendor SMS guesses (EXPLICIT HYPOTHESES, test forms only) ---
        step(ser, "AT+ECMG=?", "MTK vendor SMS guess (test)", rows)
        step(ser, "AT+ECMGS=?", "MTK vendor SMS send guess (test)", rows)
        step(ser, "AT+ECAMS=?", "MTK vendor SMS-async guess (test)", rows)

        # --- re-verify the CMER message-indicator path (reversible) ---
        step(ser, "AT+CIND?", "indicator snapshot (message/smsfull)", rows)
        step(ser, "AT+CMER=3,0,0,1", "enable indicator URCs (reversible)", rows)
        step(ser, "AT+CMER=0,0,0,0", "restore (indicators off)", rows)

    except AbortSession as e:
        print(f"\n!! ABORT: {e}", flush=True)
        rows.append(("(ABORT)", str(e), "", "ABORT"))
    finally:
        ser.close()
        RAW_LOG.close()

    with open(ROOT / "docs/at-probes/at_results6.md", "w") as f:
        f.write(f"# AT probe phase 6 — SMS completeness sweep — "
                f"{datetime.now():%Y-%m-%d %H:%M:%S} — {PORT}\n\n")
        f.write("| Command | Note | Verdict | Response |\n|---|---|---|---|\n")
        for cmd, note, resp, verdict in rows:
            r = resp.replace("|", "\\|").replace("\n", " ⏎ ")
            f.write(f"| `{cmd}` | {note} | {verdict} | "
                    f"`{r if r else '(none)'}` |\n")
    print(f"\nWrote docs/at-probes/at_results6.md ({len(rows)} steps)")


if __name__ == "__main__":
    main()
