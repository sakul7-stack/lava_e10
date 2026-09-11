# AT probe phase 3 — 2026-09-11 17:54:48 — /dev/ttyACM0

| Command | Note | Verdict | Response |
|---|---|---|---|
| `AT` | handshake | OK | `OK` |
| `ATE0` | echo off | OK | `OK` |
| `AT+CMEE=1` | verbose errors | OK | `OK` |
| `AT+CIND=?` | enumerate indicator names | OK | `+CIND:("battchg",(0-5)), ("signal",(0-5)), ("service",(0,1)), ("message",(0,1)),("call",(0,1)), ("roam",(0,1)), ("smsfull",(0,1)) ⏎ OK` |
| `AT+CLCC=?` | list-calls test form | OK | `OK` |
| `AT+VTD=?` | DTMF duration test form | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+VTS=?` | DTMF test form | OK | `+VTS: 0,1,2,3,4,5,6,7,8,9,A,B,C,D,#,* ⏎ OK` |
| `AT+CALM?` | alert tone mode (read) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CLVL?` | loudspeaker volume (read) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CVOICE=?` | voice mode test form | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CTZU=?` | timezone update test form | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CTZR=?` | timezone reporting test form | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CPOL?` | preferred operator list (read) | CME/CMS ERROR | `+CME ERROR: 100` |
| `AT+CMER=3,0,0,1` | enable indicator URCs (reversible) | OK | `OK` |
| `AT+CMER=0,0,0,0` | restore state | OK | `OK` |
| `AT+CSCS?` | restore state | OK | `+CSCS: "IRA" ⏎ OK` |
