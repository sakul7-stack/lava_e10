# AT probe phase 4 — TekBuster vendor commands (gated) — 2026-09-11 18:43:53 — /dev/ttyACM0

| Command | Note | Verdict | Response |
|---|---|---|---|
| `AT` | handshake | OK | `OK` |
| `ATE0` | echo off | OK | `OK` |
| `AT+CMEE=1` | verbose errors on | OK | `OK` |
| `AT+CMEE=2` | numeric errors (TekBuster default, reversible) | OK | `OK` |
| `AT+CMEE=1` | back to verbose errors | OK | `OK` |
| `AT+EGMR=?` | EGMR test form (proprietary) | OK | `+EGMR: (0,1),(0-5,7-12) ⏎ OK` |
| `AT+EGMR=0,0` | read CPU/hardware info | OK | `+EGMR: "MT6261" ⏎ OK` |
| `AT+EGMR=0,3` | read firmware info | OK | `+EGMR: "Lava_E10_61D_INT_T005_210714" ⏎ OK` |
| `AT+EGMR=0,4` | read hardware revision | OK | `+EGMR: "LAVA61D_11C_HW" ⏎ OK` |
| `AT+EGMR=0,7` | read IMEI SIM1 (output masked) | OK | `+EGMR: "<IMEI_REDACTED>" ⏎ OK` |
| `AT+ESUO=?` | ESUO test form | OK | `+ESUO: (4-5) ⏎ OK` |
| `AT+ESUO?` | ESUO read form (current SIM for AT channel) | OK | `+ESUO: 4, 4 ⏎ OK` |
| `AT+CMGF=?` | SMS mode test (no ESUO) - baseline | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CPBS=?` | phonebook storage test (no ESUO) - baseline | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CIMI` | IMSI read (no ESUO) - baseline (masked) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CKPD=?` | keypad emulation test form | OK | `OK` |
| `AT+CKPD="0"` | press key 0 (benign, visible on handset) | OK | `OK` |
| `AT+ESIMS=?` | SIM status query (MTK proprietary, test) | OK | `SIM1 STATUS: 0 ⏎  SIM2 STATUS: 0 ⏎ OK` |
| `AT+ESIMS?` | SIM status query (MTK proprietary, read) | OK | `SIM1 STATUS: 0 ⏎  SIM2 STATUS: 0 ⏎ OK` |
| `AT+EFUN=?` | phone-function alternative to CFUN (test) | OK | `OK` |
| `AT+EFUN?` | phone-function alternative to CFUN (read) | OK | `+EFUN: 1 ⏎ OK` |
| `AT+ESUO=3` | select SIM1 (current=4, will restore) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CMEE=1` | ensure verbose errors restored | OK | `OK` |
| `AT+CSCS?` | verify charset state | OK | `+CSCS: "IRA" ⏎ OK` |
