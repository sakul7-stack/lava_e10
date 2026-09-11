#!/usr/bin/env python3
"""Mock MediaTek-ish AT modem on a pty for testing the at_probe*.py scripts.

Emulates the observed Lava E10 behavior (CGMM/CGMR/CSQ/COPS/CFUN/CSCS work,
most other standard commands ERROR, verbose CME errors when CMEE=1) plus:

- vendor commands: AT+EGMR (read forms; IMEI read returns a FAKE IMEI),
  AT+ESUO (stateful SIM selection), AT+CKPD, AT+ESIMS, AT+EFUN
- ESUO gating: SMS/phonebook/IMSI commands only work after AT+ESUO=3
  (mirrors the TekBuster hypothesis about MT62xx firmware)
- stateful CMEE (0/1/2), CMGF, and ESUO state

Usage: python3 mock_modem.py   -> prints pty path (e.g. /dev/pts/5)
"""
import os
import pty
import sys
import time

S = {"cmee": 0, "esuo": 0, "cmgf": None}   # session state

FAKE_IMEI = "356938035643809"               # fake -> must be masked
FAKE_IMSI = "404005123456789"               # fake -> must be masked
FAKE_MSISDN = "+919999999999"               # fake -> must be masked

CME_TEXT = {3: "operation not allowed", 10: "SIM not inserted",
            100: "unknown"}


def cme(code, text=False):
    if S["cmee"] == 1:
        return f"+CME ERROR: {code} ({CME_TEXT.get(code, 'unknown')})"
    if S["cmee"] == 2:
        return f"+CME ERROR: {code}"
    return "ERROR"


def reply_for(cmd: str):
    """Return list of reply lines for a command, based on current state."""
    gated_ok = S["esuo"] == 3        # SIM1 selected -> SMS/phonebook unlocked

    # --- session/control ---
    if cmd in ("AT", "ATE0", "ATE1"):
        return ["OK"]
    if cmd == "AT+CMEE=?":
        return ["+CMEE: (0-2)", "OK"]
    if cmd == "AT+CMEE=1":
        S["cmee"] = 1
        return ["OK"]
    if cmd == "AT+CMEE=2":
        S["cmee"] = 2
        return ["OK"]
    if cmd == "AT+CMEE=0":
        S["cmee"] = 0
        return ["OK"]

    # --- identification (works) ---
    if cmd == "AT+CGMM":
        return ["+CGMM: MTK2", "OK"]
    if cmd == "AT+CGMR":
        return ["+CGMR: MOCK_E10_61D_INT_T005_210714, 2021/07/14 13:57", "OK"]
    if cmd in ("ATI", "AT+CGMI", "AT+CGSN", "AT+GCAP", "AT+CLAC"):
        return [cme(100)]

    # --- standard queries (work) ---
    if cmd == "AT+CSQ":
        return ["+CSQ: 23, 99", "OK"]
    if cmd == "AT+COPS?":
        return ["+COPS: 0", "OK"]
    if cmd == "AT+CFUN?":
        return ["+CFUN: 1", "OK"]
    if cmd == "AT+CSCS?":
        return ['+CSCS: "IRA"', "OK"]
    if cmd == "AT+CSCS=?":
        return ['+CSCS: ("IRA","GSM","HEX","PCCP437","8859-1","UCS2","UCS2_0X81")', "OK"]

    # --- MTK vendor: EGMR (read forms only; the prober never sends =1,...) ---
    if cmd == "AT+EGMR=?":
        return ["+EGMR: (0),(0,3,4,7,10,11,12),(0-15)", "OK"]
    if cmd.startswith("AT+EGMR=1,"):
        # IMEI WRITE - must never appear in probe logs; mock refuses loudly
        return [cme(3)]
    if cmd == "AT+EGMR=0,0":
        return ['+EGMR: "MTK2 CPU, MT6261D"', "OK"]
    if cmd == "AT+EGMR=0,3":
        return ['+EGMR: "MOCK_E10_61D_INT_T005_210714"', "OK"]
    if cmd == "AT+EGMR=0,4":
        return ['+EGMR: "E10_HW_1.0"', "OK"]
    if cmd == "AT+EGMR=0,7":
        return [f'+EGMR: "{FAKE_IMEI}"', "OK"]
    if cmd.startswith("AT+EGMR="):
        return [cme(100)]

    # --- MTK vendor: ESUO (stateful SIM selection) ---
    if cmd == "AT+ESUO=?":
        return ["+ESUO: (0-6)", "OK"]
    if cmd == "AT+ESUO?":
        return [f"+ESUO: {S['esuo']}", "OK"]
    if cmd in ("AT+ESUO=3", "AT+ESUO=4", "AT+ESUO=5", "AT+ESUO=6",
               "AT+ESUO=0", "AT+ESUO=1", "AT+ESUO=2"):
        S["esuo"] = int(cmd.split("=")[1])
        return ["OK"]

    # --- gated standard commands (work only after ESUO=3) ---
    if cmd == "AT+CMGF=?":
        return ["+CMGF: (0,1)", "OK"] if gated_ok else [cme(100)]
    if cmd == "AT+CMGF?":
        if not gated_ok:
            return [cme(100)]
        return [f"+CMGF: {S['cmgf']}" if S["cmgf"] is not None
                else "+CMGF: 1", "OK"]
    if cmd in ("AT+CMGF=0", "AT+CMGF=1"):
        if not gated_ok:
            return [cme(100)]
        S["cmgf"] = int(cmd.split("=")[1])
        return ["OK"]
    if cmd == "AT+CMGS=?":
        return ["+CMGS: (0-160)", "OK"] if gated_ok else [cme(100)]
    if cmd.startswith("AT+CMGS="):
        # prompt for message body -> the prober must ABORT on seeing it
        return ["> "]
    if cmd == "AT+CPBS=?":
        return ['+CPBS: ("SM","ME","FD")', "OK"] if gated_ok else [cme(100)]
    if cmd == "AT+CIMI":
        return [FAKE_IMSI, "OK"] if gated_ok else [cme(100)]
    if cmd == "AT+CNUM":
        return [f'+CNUM: "Fake",{FAKE_MSISDN},129', "OK"]

    # --- MTK vendor: keypad / SIM status / EFUN ---
    if cmd == "AT+CKPD=?":
        return ["+CKPD: (0-9,*,#,A-D,[,],<,>,^,v,m,s,e)", "OK"]
    if cmd.startswith("AT+CKPD="):
        S.setdefault("ckpd", []).append(cmd)
        return ["OK"]
    if cmd == "AT+ESIMS=?":
        return ["+ESIMS: (0-1)", "OK"]
    if cmd == "AT+ESIMS?":
        return ["+ESIMS: 1", "OK"]
    if cmd == "AT+EFUN=?":
        return ["+EFUN: (0-1)", "OK"]
    if cmd == "AT+EFUN?":
        return ["+EFUN: 1", "OK"]

    # --- everything else: parser-level unknown ---
    return [cme(100)]


def main():
    mfd, sfd = pty.openpty()
    name = os.ttyname(sfd)
    print(name, flush=True)
    buf = b""
    while True:
        try:
            data = os.read(mfd, 256)
        except OSError:
            break
        if not data:
            continue
        buf += data
        while b"\r" in buf:
            line, buf = buf.split(b"\r", 1)
            cmd = line.decode("latin-1").strip()
            if not cmd:
                continue
            out = ("\r\n".join(reply_for(cmd)) + "\r\n").encode()
            os.write(mfd, out)
            time.sleep(0.01)


if __name__ == "__main__":
    main()
