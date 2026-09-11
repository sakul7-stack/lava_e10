#!/usr/bin/env python3
"""Phase-4 probe: TekBuster-informed vendor AT commands for Lava E10 / MT62xx.

Safety discipline (hard rules, enforced in code):
- Test order per command: AT+X=? -> AT+X? -> write form, and a write form is
  sent ONLY as a gated step whose precondition (earlier verdicts) is met.
- NO IMEI writes: the AT+EGMR=1,... family is never in the plan.
- NO CFUN=0/4, NO CPBW, no NV/flash/network writes of any kind.
- AT+ESUO=<n> is only sent when the CURRENT value is known from AT+ESUO?
  (so the original state can be restored afterwards).
- If the modem ever emits an SMS input prompt ('>'), the session aborts
  immediately so no message body can ever be composed.
- Every response is masked for >=12-digit runs (IMEI/IMSI/MSISDN-like).

Raw bytes -> at_raw4.log ; results -> at_results4.md.
Usage: python3 at_probe4.py [PORT]   (default /dev/ttyACM0)
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
LONG_CMDS = {"AT+ESUO=?": 8.0}
RAW_LOG = open(ROOT / "captured-output/at/at_raw4.log", "wb", buffering=0)

# Static plan: (command, note, gates)
# gates = list of (earlier_command, {acceptable verdicts}); ALL must pass.
# A gated step whose gate fails is recorded as SKIPPED, never sent.
PLAN = [
    # --- Stage 0: session init (TekBuster protocol) ---
    ("AT",            "handshake", []),
    ("ATE0",          "echo off", []),
    ("AT+CMEE=1",     "verbose errors on", []),
    ("AT+CMEE=2",     "numeric errors (TekBuster default, reversible)", []),
    ("AT+CMEE=1",     "back to verbose errors", []),

    # --- Stage 1: MTK proprietary EGMR, READ forms only (never =1,...) ---
    ("AT+EGMR=?",     "EGMR test form (proprietary)", []),
    ("AT+EGMR=0,0",   "read CPU/hardware info",
     [("AT+EGMR=?", {"OK"})]),
    ("AT+EGMR=0,3",   "read firmware info",
     [("AT+EGMR=?", {"OK"})]),
    ("AT+EGMR=0,4",   "read hardware revision",
     [("AT+EGMR=?", {"OK"})]),
    ("AT+EGMR=0,7",   "read IMEI SIM1 (output masked)",
     [("AT+EGMR=?", {"OK"})]),

    # --- Stage 2: MTK proprietary SIM selection (ESUO) ---
    ("AT+ESUO=?",     "ESUO test form", []),
    ("AT+ESUO?",      "ESUO read form (current SIM for AT channel)", []),

    # --- Stage 3: baseline retests WITHOUT ESUO (test/read forms only) ---
    ("AT+CMGF=?",     "SMS mode test (no ESUO) - baseline", []),
    ("AT+CPBS=?",     "phonebook storage test (no ESUO) - baseline", []),
    ("AT+CIMI",       "IMSI read (no ESUO) - baseline (masked)", []),

    # --- Stage 4: keypad emulation ---
    ("AT+CKPD=?",     "keypad emulation test form", []),
    ('AT+CKPD="0"',   "press key 0 (benign, visible on handset)",
     [("AT+CKPD=?", {"OK"})]),

    # --- Stage 5: other MTK vendor probes (test/read forms only) ---
    ("AT+ESIMS=?",    "SIM status query (MTK proprietary, test)", []),
    ("AT+ESIMS?",     "SIM status query (MTK proprietary, read)", []),
    ("AT+EFUN=?",     "phone-function alternative to CFUN (test)", []),
    ("AT+EFUN?",      "phone-function alternative to CFUN (read)", []),
]

# Post-ESUO retests (test/read forms + gated CMGF write)
POST_ESUO = [
    ("AT+CMGF=?",     "SMS mode test (after ESUO)"),
    ("AT+CMGF=0",     "set SMS PDU mode (standard 27.005, reversible)",
     [("AT+CMGF=?", {"OK"})]),
    ("AT+CMGF?",      "read SMS mode back"),
    ("AT+CMGS=?",     "SMS send test form (after ESUO)"),
    ("AT+CPBS=?",     "phonebook storage test (after ESUO)"),
    ("AT+CIMI",       "IMSI read (after ESUO) - masked"),
    ("AT+CNUM",       "subscriber number (after ESUO) - masked"),
]

MASK = re.compile(rb"(?<!\d)(\d{4})\d{6,}(\d{2})(?!\d)")
# SMS input prompt: a line containing only '>' (SMS body request) -> abort.
# Matches both '> ' (unterminated) and '> \r\n' (terminated line).
PROMPT = re.compile(rb"(?:^|\r\n)>\s*(?:\r\n)?$")


class AbortSession(Exception):
    pass


def read_some(ser, buf):
    n = ser.in_waiting
    if n:
        chunk = ser.read(n)
        buf.extend(chunk)
        RAW_LOG.write(chunk)


def send(ser, cmd):
    cap_s = LONG_CMDS.get(cmd, HARD_CAP)
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
            raise AbortSession("SMS input prompt '>' observed - aborting "
                               "so no message body can ever be sent")
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
    if ">" in resp:
        return "PROMPT"
    return "DATA/OTHER"


def gates_ok(results, gates):
    for earlier, allowed in gates:
        if results.get(earlier) not in allowed:
            return earlier
    return None


def run_step(ser, cmd, note, results, rows, gates=()):
    blocked = gates_ok(results, gates)
    if blocked:
        verdict = f"SKIPPED (gate: '{blocked}' did not pass)"
        resp = ""
    else:
        resp = send(ser, cmd)
        verdict = classify(resp)
    results[cmd] = verdict
    rows.append((cmd, note, resp, verdict))
    disp = resp[:120].replace("\n", " ⏎ ")
    print(f"  {cmd:<24} {verdict:<34} | {disp}", flush=True)
    return resp, verdict


def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    results, rows = {}, []
    abort_note = None
    print(f"Phase-4 TekBuster probe (gated) — {datetime.now():%Y-%m-%d %H:%M:%S} — {PORT}\n",
          flush=True)
    try:
        for cmd, note, gates in PLAN:
            run_step(ser, cmd, note, results, rows, gates)

        # --- Dynamic ESUO branch: write only if current value is known ---
        # (dict of every response so far, keyed by command)
        responses = {cmd: resp for cmd, _, resp, _ in rows}
        esuo_cur = None
        if results.get("AT+ESUO?", "").startswith(("OK", "DATA")):
            m = re.search(r"\+ESUO:\s*(\d+)", responses.get("AT+ESUO?", ""))
            if m:
                esuo_cur = int(m.group(1))
        esuo_changed = False
        post_unlocked = False

        if results.get("AT+ESUO=?", "") == "OK" and esuo_cur is not None:
            if esuo_cur != 3:
                _, verdict = run_step(ser, "AT+ESUO=3",
                                      f"select SIM1 (current={esuo_cur}, will restore)",
                                      results, rows)
                esuo_changed = verdict == "OK"
            else:
                print("  (AT+ESUO already 3 - no write needed)", flush=True)
            if esuo_cur == 3 or esuo_changed:
                post_unlocked = True
        else:
            print("  (ESUO write skipped: current value unknown or command "
                  "absent - cannot guarantee restore)", flush=True)

        if post_unlocked:
            for entry in POST_ESUO:
                cmd, note = entry[0], entry[1]
                gates = entry[2] if len(entry) > 2 else []
                run_step(ser, cmd, note, results, rows, gates)

        # --- Restore anything we changed ---
        if "AT+CMGF=0" in results and results["AT+CMGF=0"] == "OK":
            run_step(ser, "AT+CMGF=1", "restore SMS text mode", results, rows)
        if esuo_changed:
            run_step(ser, f"AT+ESUO={esuo_cur}",
                     f"restore original ESUO value ({esuo_cur})", results, rows)
        run_step(ser, "AT+CMEE=1", "ensure verbose errors restored", results, rows)
        run_step(ser, "AT+CSCS?", "verify charset state", results, rows)

    except AbortSession as e:
        abort_note = str(e)
        print(f"\n!! ABORT: {abort_note}", flush=True)
        # best-effort: just close; nothing stateful was mid-write
    finally:
        ser.close()
        RAW_LOG.close()

    with open(ROOT / "docs/at-probes/at_results4.md", "w") as f:
        f.write(f"# AT probe phase 4 — TekBuster vendor commands (gated) — "
                f"{datetime.now():%Y-%m-%d %H:%M:%S} — {PORT}\n\n")
        if abort_note:
            f.write(f"**SESSION ABORTED:** {abort_note}\n\n")
        f.write("| Command | Note | Verdict | Response |\n|---|---|---|---|\n")
        for cmd, note, resp, verdict in rows:
            r = resp.replace("|", "\\|").replace("\n", " ⏎ ")
            f.write(f"| `{cmd}` | {note} | {verdict} | "
                    f"`{r if r else '(not sent)'}` |\n")
    print(f"\n{'=' * 60}")
    print(f"Wrote docs/at-probes/at_results4.md ({len(rows)} steps)")
    ok = sum(1 for *_ , v in rows if v == "OK")
    err = sum(1 for *_, v in rows if "ERROR" in v)
    skip = sum(1 for *_, v in rows if v.startswith("SKIPPED"))
    print(f"  OK: {ok}  ERROR: {err}  SKIPPED: {skip}")
    if abort_note:
        print(f"  ABORTED: {abort_note}")


if __name__ == "__main__":
    main()
