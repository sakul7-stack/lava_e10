# AT probe phase 2 — 2026-09-11 17:52:51 — /dev/ttyACM0

| Command | Note | Verdict | Response |
|---|---|---|---|
| `AT` | handshake | OK | `OK` |
| `ATE0` | echo off | OK | `OK` |
| `AT+CMEE=1` | verbose errors on | OK | `OK` |
| `AT+CGMR` | recheck firmware id | OK | `+CGMR: Lava_E10_61D_INT_T005_210714, 2021/07/14 13:57 ⏎ OK` |
| `AT+CGMM` | recheck model | OK | `+CGMM: MTK2 ⏎ OK` |
| `AT+CFUN?` | recheck functionality | OK | `+CFUN: 1 ⏎ OK` |
| `AT+CIND?` | indicator control (MTK favorite) | OK | `+CIND: 5,5,0,0,0,0,0 ⏎ OK` |
| `AT+CMER=?` | indicator event reporting (test) | OK | `+CMER: (0-3), (0-2), (0), (0-2), (0,1) ⏎ OK` |
| `AT+CR?` | service reporting | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CRC?` | ring type (read) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CLCC` | list current calls (read-only) | OK | `OK` |
| `AT+CSCB?` | cell broadcast (read) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CSCA=?` | service center (test form) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CPMS=?` | message storage (test form) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CMGF?` | SMS mode (read form) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CMUX=?` | 27.010 multiplexer (test) — could give more channels | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CGREG?` | GPRS registration (read) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CGPADDR` | PDP address (read) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CGEREP=?` | URC reporting (test) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CLIP=?` | calling line id (test) | OK | `+CLIP: (0-1) ⏎ OK` |
| `AT+CHLD=?` | call hold (test) | OK | `+CHLD: (0, 1, 1x, 2, 2x, 3, 4, 5) ⏎ OK` |
| `AT+CVHU=?` | voice hangup (test) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CSQ` | signal again | OK | `+CSQ: 29, 99 ⏎ OK` |
| `AT+COPS?` | operator mode | OK | `+COPS: 0 ⏎ OK` |
| `AT+CSCS?` | current charset | OK | `+CSCS: "IRA" ⏎ OK` |
