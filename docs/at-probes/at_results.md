# Automated AT probe — 2026-09-11 17:49:08 — /dev/ttyACM0

| Command | Note | Verdict | Response |
|---|---|---|---|
| `AT` | handshake | OK | `OK` |
| `ATE0` | echo off (reversible) | OK | `OK` |
| `AT+CMEE=?` | error-report test form | OK | `+CMEE: (0-2) ⏎ OK` |
| `AT+CMEE=1` | enable verbose errors (reversible) | OK | `OK` |
| `ATI` | retry: identification | CME/CMS ERROR (verbose!) | `+CME ERROR: 100` |
| `AT+CGMI` | retry: manufacturer | CME/CMS ERROR (verbose!) | `+CME ERROR: 100` |
| `AT+CGSN` | retry: IMEI (masked) | CME/CMS ERROR (verbose!) | `+CME ERROR: 100` |
| `AT+CREG?` | retry: registration | CME/CMS ERROR (verbose!) | `+CME ERROR: 100` |
| `AT+CPIN?` | retry: SIM status | CME/CMS ERROR (verbose!) | `+CME ERROR: 100` |
| `AT+CMGF=?` | retry: SMS mode | CME/CMS ERROR (verbose!) | `+CME ERROR: 100` |
| `AT+CPAS?` | phone activity status | CME/CMS ERROR (verbose!) | `+CME ERROR: 100` |
| `AT+CBC?` | battery charge | CME/CMS ERROR (verbose!) | `+CME ERROR: 100` |
| `AT+CCLK?` | real-time clock | CME/CMS ERROR (verbose!) | `+CME ERROR: 100` |
| `AT+CGATT?` | GPRS attach state | CME/CMS ERROR (verbose!) | `+CME ERROR: 100` |
| `AT+CGDCONT?` | PDP contexts (read) | CME/CMS ERROR (verbose!) | `+CME ERROR: 100` |
| `AT+CESQ` | extended signal quality | CME/CMS ERROR (verbose!) | `+CME ERROR: 100` |
| `AT+CSQ` | signal quality | OK | `+CSQ: 29, 99 ⏎ OK` |
| `AT+CSCS=?` | available character sets | OK | `+CSCS: ("IRA", "GSM", "HEX", "PCCP437", "8859-1", "UCS2", "UCS2_0X81") ⏎ OK` |
| `AT+CGMM=?` | model test form | OK | `OK` |
| `AT+CGMR=?` | firmware test form | OK | `OK` |
| `AT+CGMI=?` | manufacturer test form | CME/CMS ERROR (verbose!) | `+CME ERROR: 100` |
| `AT+CREG=?` | registration test form | CME/CMS ERROR (verbose!) | `+CME ERROR: 100` |
| `AT+CPIN=?` | SIM test form | CME/CMS ERROR (verbose!) | `+CME ERROR: 100` |
| `AT+CIMI` | IMSI (masked) | CME/CMS ERROR (verbose!) | `+CME ERROR: 100` |
| `AT+CNUM` | subscriber number (masked) | OK | `OK` |
| `AT+GCAP` | retry: capabilities | CME/CMS ERROR (verbose!) | `+CME ERROR: 100` |
| `AT+CLAC` | retry: list commands | CME/CMS ERROR (verbose!) | `+CME ERROR: 100` |
| `AT+COPS=?` | operator scan (slow, read-only) | OK | `+COPS: (2,"42901","42901","42901",0),(1,"42902","42902","42902",0),,(0-3),(0-2) ⏎ OK` |
