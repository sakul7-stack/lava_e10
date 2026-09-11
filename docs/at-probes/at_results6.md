# AT probe phase 6 — SMS completeness sweep — 2026-09-11 19:04:22 — /dev/ttyACM0

| Command | Note | Verdict | Response |
|---|---|---|---|
| `AT` | handshake | OK | `OK` |
| `ATE0` | echo off | OK | `OK` |
| `AT+CMEE=1` | verbose errors | OK | `OK` |
| `AT+ESIMS?` | SIM presence recheck | OK | `SIM1 STATUS: 0 ⏎  SIM2 STATUS: 0 ⏎ OK` |
| `AT+CMGR=?` | SMS read (test) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CMGW=?` | SMS write to storage (test) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CMGD=?` | SMS delete (test) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CMSS=?` | SMS send from storage (test) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CNMA=?` | new-message acknowledgement (test) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CSMP=?` | SMS text-mode parameters (test) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CSCB=?` | cell broadcast types (test) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CMGC=?` | SMS command (test) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CSMS=?` | message service selection (test) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CSAS=?` | save SMS settings (test) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CRES=?` | restore SMS settings (test) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CPMS?` | preferred message storage (read) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CSCA?` | service centre address (read) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+ECMG=?` | MTK vendor SMS guess (test) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+ECMGS=?` | MTK vendor SMS send guess (test) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+ECAMS=?` | MTK vendor SMS-async guess (test) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CIND?` | indicator snapshot (message/smsfull) | OK | `+CIND: 5,5,0,0,0,0,0 ⏎ OK` |
| `AT+CMER=3,0,0,1` | enable indicator URCs (reversible) | OK | `OK` |
| `AT+CMER=0,0,0,0` | restore (indicators off) | OK | `OK` |
