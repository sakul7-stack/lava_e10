#!/usr/bin/env python3
"""Phase-4b probe: close the ESUO gating hypothesis + EGMR read sweep.

Safety discipline (hard rules, enforced in code):
- Every write value is parsed from the command's OWN test-form response first;
  a value outside the reported range is never sent.
- AT+ESUO write: only 4/5 (from AT+ESUO=?), current value read beforehand and
  restored afterwards.
- EGMR: read forms only (AT+EGMR=0,<idx>); the =1 (write) mode is never sent.
- No CPBW, no CFUN=0/4, no NV/flash writes.
- SMS prompt '>' aborts the session instantly.
- IMEI/IMSI/MSISDN-like output masked.

Raw bytes -> at_raw4b.log ; results -> at_results4b.md.
Usage: python3 at_probe4b.py [PORT]   (default /dev/ttyACM0)
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
RAW_LOG = open(ROOT / "captured-output/at/at_raw4b.log", "wb", buffering=0)

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
            raise AbortSession("SMS input prompt '>' observed - aborting")
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


def step(ser, cmd, note, rows, cap_s=HARD_CAP):
    resp = send(ser, cmd, cap_s)
    verdict = classify(resp)
    rows.append((cmd, note, resp, verdict))
    print(f"  {cmd:<22} {verdict:<14} | {resp[:100].replace(chr(10), ' | ')}",
          flush=True)
    return resp, verdict


def parse_range(resp):
    """Parse '(4-5)' / '(0,1)' style ranges out of a test-form response."""
    vals = set()
    for lo, hi in re.findall(r"\((\d+)-(\d+)\)", resp):
        vals.update(range(int(lo), int(hi) + 1))
    for v in re.findall(r"\((\d+)\)", resp):
        vals.add(int(v))
    return vals


def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    rows = []
    print(f"Phase-4b probe — {datetime.now():%Y-%m-%d %H:%M:%S} — {PORT}\n",
          flush=True)
    try:
        # --- init ---
        step(ser, "AT", "handshake", rows)
        step(ser, "ATE0", "echo off", rows)
        step(ser, "AT+CMEE=1", "verbose errors", rows)

        # --- EGMR read sweep (read-only indices from test form) ---
        resp, _ = step(ser, "AT+EGMR=?", "EGMR test form (reference)", rows)
        for idx in (1, 2, 5):
            step(ser, f"AT+EGMR=0,{idx}", f"read EGMR index {idx} (read-only)",
                 rows)

        # --- ESUO: write ONLY values parsed from its own test form ---
        resp, _ = step(ser, "AT+ESUO=?", "ESUO test form", rows)
        allowed = parse_range(resp)
        resp_cur, _ = step(ser, "AT+ESUO?", "ESUO current value", rows)
        m = re.search(r"\+ESUO:\s*(\d+)", resp_cur)
        cur = int(m.group(1)) if m else None
        print(f"  [ESUO allowed={sorted(allowed)} current={cur}]", flush=True)

        if allowed and cur is not None and cur in allowed:
            other = sorted(v for v in allowed if v != cur)
            if other:
                tgt = other[-1]   # the other SIM slot
                step(ser, f"AT+ESUO={tgt}",
                     f"select other SIM ({tgt}; current {cur}, will restore)",
                     rows)
                step(ser, "AT+ESUO?", "confirm switch", rows)
                # retest the gated standard set (test/read forms only)
                step(ser, "AT+CMGF=?", "SMS mode test (other SIM)", rows)
                step(ser, "AT+CMGS=?", "SMS send test (other SIM)", rows)
                step(ser, "AT+CPMS=?", "SMS storage test (other SIM)", rows)
                step(ser, "AT+CPBS=?", "phonebook test (other SIM)", rows)
                step(ser, "AT+CIMI", "IMSI read (other SIM) - masked", rows)
                # restore
                step(ser, f"AT+ESUO={cur}",
                     f"restore original ESUO ({cur})", rows)
                step(ser, "AT+ESUO?", "verify restore", rows)
        else:
            print("  (ESUO branch skipped: range/current unknown)", flush=True)

        # --- final state verification ---
        step(ser, "AT+CMEE=1", "ensure verbose errors", rows)
        step(ser, "AT+CSCS?", "charset state", rows)
        step(ser, "AT+CFUN?", "functionality state", rows)

    except AbortSession as e:
        print(f"\n!! ABORT: {e}", flush=True)
        rows.append(("(ABORT)", str(e), "", "ABORT"))
    finally:
        ser.close()
        RAW_LOG.close()

    with open(ROOT / "docs/at-probes/at_results4b.md", "w") as f:
        f.write(f"# AT probe phase 4b — ESUO gating falsification + EGMR sweep — "
                f"{datetime.now():%Y-%m-%d %H:%M:%S} — {PORT}\n\n")
        f.write("| Command | Note | Verdict | Response |\n|---|---|---|---|\n")
        for cmd, note, resp, verdict in rows:
            r = resp.replace("|", "\\|").replace("\n", " ⏎ ")
            f.write(f"| `{cmd}` | {note} | {verdict} | "
                    f"`{r if r else '(none)'}` |\n")
    print(f"\nWrote docs/at-probes/at_results4b.md ({len(rows)} steps)")


if __name__ == "__main__":
    main()
