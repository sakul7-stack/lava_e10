# AT probe phase 4b — ESUO gating falsification + EGMR sweep — 2026-09-11 18:45:59 — /dev/ttyACM0

| Command | Note | Verdict | Response |
|---|---|---|---|
| `AT` | handshake | OK | `OK` |
| `ATE0` | echo off | OK | `OK` |
| `AT+CMEE=1` | verbose errors | OK | `OK` |
| `AT+EGMR=?` | EGMR test form (reference) | OK | `+EGMR: (0,1),(0-5,7-12) ⏎ OK` |
| `AT+EGMR=0,1` | read EGMR index 1 (read-only) | OK | `+EGMR: "2000.00.00" ⏎ OK` |
| `AT+EGMR=0,2` | read EGMR index 2 (read-only) | OK | `+EGMR: "1.0" ⏎ OK` |
| `AT+EGMR=0,5` | read EGMR index 5 (read-only) | OK | `+EGMR: "<DEVICE_ID_REDACTED>" ⏎ OK` |
| `AT+ESUO=?` | ESUO test form | OK | `+ESUO: (4-5) ⏎ OK` |
| `AT+ESUO?` | ESUO current value | OK | `+ESUO: 4, 4 ⏎ OK` |
| `AT+ESUO=5` | select other SIM (5; current 4, will restore) | OK | `OK` |
| `AT+ESUO?` | confirm switch | OK | `+ESUO: 5, 4 ⏎ OK` |
| `AT+CMGF=?` | SMS mode test (other SIM) | ERROR | `ERROR` |
| `AT+CMGS=?` | SMS send test (other SIM) | ERROR | `ERROR` |
| `AT+CPMS=?` | SMS storage test (other SIM) | ERROR | `ERROR` |
| `AT+CPBS=?` | phonebook test (other SIM) | ERROR | `ERROR` |
| `AT+CIMI` | IMSI read (other SIM) - masked | ERROR | `ERROR` |
| `AT+ESUO=4` | restore original ESUO (4) | OK | `OK` |
| `AT+ESUO?` | verify restore | OK | `+ESUO: 4, 4 ⏎ OK` |
| `AT+CMEE=1` | ensure verbose errors | OK | `OK` |
| `AT+CSCS?` | charset state | OK | `+CSCS: "IRA" ⏎ OK` |
| `AT+CFUN?` | functionality state | OK | `+CFUN: 1 ⏎ OK` |
