# TekBuster Source Analysis — 2026-09-11

## Source

- **URL:** https://tekbuster.surge.sh (WebUSB-based browser toolkit)
- **Library:** `buster.js` (233 lines, downloadable from the site)
- **Author:** plugnburn (same as NokiaTool gist)
- **Target platform:** MediaTek MT62xx feature phones (MT6261 primary, MT6260A/MT6276 also supported)
- **License:** Open (embed/use with attribution)

## AT Commands Used by TekBuster

| Command | Purpose | Category |
|---|---|---|
| `AT` | Handshake | Standard V.25ter |
| `AT+CMEE=2` | Enable numeric error codes | Standard 27.007 |
| `AT+EGMR=0,0` | Read CPU/hardware info | **MTK proprietary** |
| `AT+EGMR=0,3` | Read firmware info | **MTK proprietary** |
| `AT+EGMR=0,4` | Read hardware revision | **MTK proprietary** |
| `AT+EGMR=0,7` | Read IMEI (SIM1) | **MTK proprietary** |
| `AT+EGMR=0,10` | Read IMEI (SIM2) | **MTK proprietary** |
| `AT+EGMR=0,11` | Read IMEI (SIM3) | **MTK proprietary** |
| `AT+EGMR=0,12` | Read IMEI (SIM4) | **MTK proprietary** |
| `AT+EGMR=1,<sim>,<imei>` | Write IMEI | **MTK proprietary** WARNING |
| `AT+ESUO=?` | Query SIM operation modes | **MTK proprietary** |
| `AT+ESUO=3` | Select SIM1 for AT operations | **MTK proprietary** |
| `AT+ESUO=4` | Select SIM2 | **MTK proprietary** |
| `AT+ESUO=5` | Select SIM3 | **MTK proprietary** |
| `AT+ESUO=6` | Select SIM4 | **MTK proprietary** |
| `AT+CIMI` | Read IMSI (after ESUO) | Standard 27.007 |
| `AT+CKPD="..."` | Keypad emulation | Standard 27.007 |
| `AT+CMGF=0` | Set SMS PDU mode | Standard 27.005 |
| `AT+CMGS=<pduLen>` | Send SMS (PDU) | Standard 27.005 |
| `AT+CPBS="SM"/"ME"` | Select phonebook storage | Standard 27.007 |
| `AT+CSCS="UCS2"` | Set charset to UCS2 | Standard 27.007 |
| `AT+CPBW=,...` | Write phonebook entry | Standard 27.007 |

## TekBuster Protocol Notes

1. **Session init:** Sends `AT` × 3, then `AT+CMEE=2` (numeric errors)
2. **SIM selection:** Uses `AT+ESUO=<N>` (N = simNumber + 3) before any SIM-dependent operation
3. **SMS sending:** PDU mode only (`AT+CMGF=0`), builds PDU manually, sends via `AT+CMGS=<len>` + CTRL+Z
4. **Keypad emulation:** `AT+CKPD="<keyseq>"` — supports digits, *, #, softkeys ([ ] m), send/end (s e), arrows (< > ^ v)
5. **Contact import:** `AT+CPBS` + `AT+CSCS="UCS2"` + `AT+CPBW` with UCS2-encoded names
6. **Nokia quirk:** For Nokia phones, scans for interface class 10 (CDC Data) with 2 bulk endpoints; uses different endpoint numbering than generic MTK

## Diff vs Our Probe Results

### Commands we tested that TekBuster also uses:

| Command | Our Result | TekBuster Uses | Analysis |
|---|---|---|---|
| `AT` | OK | Yes | PASS — Match |
| `AT+CMEE=1` | OK (we used verbose) | `AT+CMEE=2` (numeric) | Both supported; TekBuster prefers numeric |
| `AT+CMGF=?` | CME ERROR: 100 | `AT+CMGF=0` (direct write) | **KEY: CMGF might work AFTER ESUO selection** |
| `AT+CIMI` | CME ERROR: 100 | Yes (after `AT+ESUO=3`) | **KEY: CIMI might work AFTER ESUO selection** |
| `AT+CPBS=?` | CME ERROR: 100 | `AT+CPBS="SM"` (direct write) | **KEY: CPBS might work AFTER ESUO selection** |
| `AT+CSCS?` | IRA | `AT+CSCS="UCS2"` (write) | We read; TekBuster writes UCS2 |

### Commands we HAVEN'T tested (TekBuster-specific):

| Command | Purpose | Risk |
|---|---|---|
| `AT+EGMR=0,0` | Read CPU info | LOW — read-only |
| `AT+EGMR=0,3` | Read firmware info | LOW — read-only |
| `AT+EGMR=0,4` | Read hardware revision | LOW — read-only |
| `AT+EGMR=0,7` | Read IMEI (SIM1) | MEDIUM — returns IMEI, must mask |
| `AT+ESUO=?` | Query SIM modes | LOW — test form |
| `AT+ESUO=3` | Select SIM1 | MEDIUM — changes state, but reversible |
| `AT+CKPD="0"` | Keypad press | LOW — just presses a key |

### Critical Hypothesis

`[HYP]` The Lava E10 firmware gates standard SMS/phonebook/SIM commands behind `AT+ESUO=<N>` SIM selection. Our probes tested `AT+CMGF=?`, `AT+CPBS=?`, `AT+CIMI` WITHOUT first running `AT+ESUO`, which may be why they all returned CME ERROR: 100. TekBuster's protocol always does `AT+ESUO=<N>` before these commands.

**Falsification test:** Run `AT+ESUO=?` to check if the command is supported, then `AT+ESUO=3` to select SIM1, then retest `AT+CMGF=?` and `AT+CPBS=?`.

## Also Referenced: NokiaTool (plugnburn gist)

NokiaTool confirms the same MTK vendor AT set for Nokia feature phones:
- `AT+CKPD` for keypad emulation
- `AT+CMGF=1` + `AT+CMGS` for SMS (text mode)
- `AT+CPBW` for phonebook writes
- `AT+EGMR` for IMEI access
- Notes that `AT+CMGL` is NOT supported on Nokia MT62xx
- Notes that `AT+CG*` (GPRS) commands are NOT supported
- Notes that `AT+CUSD`/`AT+ECUSD` are NOT supported
- Notes that `AT+ESUO=3` file system commands are NOT supported on Nokia (but this may be Nokia-specific, not platform-wide)

## Also Referenced: MTK AT Command Set (Scribd, MD230/MD231, 170pp)

The leaked MTK AT command set document (Revision 0.18, Feb 2010) confirms:
- `AT+EGMR` — "Mobile Revision and IMEI" (proprietary section 11.13)
- `AT+ESIMS` — "Query SIM Status" (proprietary section 11.14)
- `AT+CKPD` — "Keypad control" (section 8.7)
- Full TS 27.005 SMS command set (CMGF, CMGS, CMGL, CMGR, CMGW, CMGD, CNMI, CPMS, CSCA)
- Full TS 27.007 network/call commands
- `AT+EFUN` as alternative to `AT+CFUN`
- `AT+EMBT` — Bluetooth engineer mode
- Various hardware testing commands (GPIO, ADC, PWM, LCD, audio)

`[INTERP]` The MTK platform DEFINITELY has the full SMS command set compiled in at the platform level. The Lava firmware selectively exposes only a subset. The question is whether `AT+ESUO` gating is the missing piece.

## Hardware Falsification — 2026-09-11 (phase 4/4b, see ../overview/info.md §14)

`[FACT]` **The `AT+ESUO` gating hypothesis is FALSIFIED on the Lava E10.** Tested with the code-gated prober (`at_probe4.py`, `at_probe5.py`), all writes range-parsed and restored:

- `AT+ESUO=?` → `+ESUO: (4-5)`; `AT+ESUO?` → `+ESUO: 4, 4` (this firmware: SIM1=4, SIM2=5 — not the 3/4 numbering TekBuster/NokiaTool use)
- Switched to SIM2 (`AT+ESUO=5` → OK, confirmed), retested `AT+CMGF=? / AT+CMGS=? / AT+CPMS=? / AT+CPBS=? / AT+CIMI` → **all ERROR**
- Restored to `AT+ESUO=4`, verified. (Note: CMEE state resets on ESUO change.)

`[INTERP]` SMS/phonebook/IMSI commands are compiled out of this firmware's AT parser **regardless of SIM selection**. TekBuster's flow will not unlock them here; the difference is the Lava build's application-level filtering, not ESUO state.

`[FACT]` What the vendor set *did* yield on this phone: `AT+EGMR=0,0` → `"MT6261"` (chipset confirmed, `61D` hypothesis confirmed), full EGMR identity read set (0,1..5,7), `AT+CKPD` keypad emulation, `AT+ESIMS` dual-SIM status, `AT+EFUN?` → 1. The `AT+EGMR=1,...` IMEI-write form exists in the parser (`=?` shows mode 1) — **permanently out of scope**, never sent.

`[INTERP]` Remaining SMS routes on this handset: other USB modes (mass storage / sync / diagnostic) and the PC-sync proprietary protocol. USB-level sniffing of vendor sync software is now the evidence-backed next phase if the other USB modes come up empty.

## EPILOGUE (2026-09-11, ../overview/info.md §19): the native route WON

AT SMS (test AND write forms, both channels, both SIM states) is fully closed — but the phone's **native Messages app is drivable via `AT+CKPD`**, and an SMS composed and sent entirely over USB **was delivered to a real destination**. Working recipe: `../../scripts/sms/sms_native.py` (wake → End → Menu → Messages → Write new → multitap body → Options → Send To → ↑ to "Enter phone number" → digits → OK, OK). Key subtleties: first press after backlight timeout is consumed by the wake; arrows navigate even on a dark screen; in-letter multitap presses must be back-to-back.

**Lesson for MT62xx-class handsets with filtered AT sets:** before concluding "no SMS over USB", test `AT+CKPD` UI automation — the application layer (and the SIM) still speaks SMS even when the AT parser does not.
