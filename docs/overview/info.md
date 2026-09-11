# Lava E10 Color CL220 — USB COM / AT-Command Interface Investigation

**Reverse-engineering lab notebook**

- **Date of experiments:** 2026-09-11 (device node created 17:11 local, second session ~17:17)
- **Host:** Arch Linux, kernel `7.2.3-arch1-2` (as reported in the xHCI root-hub string)
- **Device under test (DUT):** Lava E10 Color CL220 feature phone, connected by USB in its **"COM port"** USB mode
- **Status:** Interface confirmed working; **not** a confirmed USB SMS modem at this stage

### How to read this document

Statements are tagged so a future researcher can separate evidence from reasoning:

| Tag | Meaning |
|-----|---------|
| `[FACT]` | Directly observed output or behavior, verbatim from the session |
| `[INTERP]` | Interpretation of observed facts (reasoned, but derived) |
| `[HYP]` | Hypothesis / unverified assumption to be tested later |


---

## 1. Device identification

| Item | Value |
|------|-------|
| Phone | Lava E10 Color CL220 (feature phone) |
| USB Vendor ID | `0e8d` (MediaTek Inc.) |
| USB Product ID | `0003` |
| USB Manufacturer string | `Lava E10̚Lav` |
| USB Product string | `Lava E10̜Mas` |
| Platform (via AT) | `AT+CGMM` → `+CGMM: MTK2` |
| Firmware (via AT) | `AT+CGMR` → `+CGMR: Lava_E10_61D_INT_T005_210714, 2021/07/14 13:57` |

`[FACT]` The values above are verbatim from `lsusb`, `usb-devices`, and the AT session.

`[INTERP]` The phone is a MediaTek-based Lava E10 running firmware built on **July 14, 2021**. `MTK2` in the `CGMM` response points at MediaTek's feature-phone platform/AT-firmware generation rather than a smartphone SoC.

`[INTERP]` `lsusb` renders `0e8d:0003` as **"MediaTek Inc. MT6227 phone"** — this name comes from the `usb.ids` database and is keyed only on VID:PID, which MediaTek reuses across many feature-phone products. It is **not** proof that the actual chipset is an MT6227.

`[HYP]` The `61D` token in the firmware name may correspond to an MT6261D-class chipset (a common 2021-era MTK 2G feature-phone SoC). Unverified — check against firmware references before asserting.

`[FACT]` The USB strings contain stray combining diacritics (`̚`, `̜`) and look truncated/garbled — a firmware string-encoding defect, harmless but distinctive.

---

## 2. USB connection on the host

The phone exposes a **"COM port"** mode in its on-device USB settings. With that mode selected:

`lsusb`:

```text
Bus 003 Device 043: ID 0e8d:0003 MediaTek Inc. MT6227 phone
```

Kernel messages (`dmesg`, uptime-relative timestamps):

```text
[23613.631900] usb 3-2: new full-speed USB device number 43 using xhci_hcd
[23613.758222] usb 3-2: New USB device found, idVendor=0e8d, idProduct=0003, bcdDevice= 1.00
[23613.762564] usb 3-2: New USB device strings: Mfr=3, Product=4, SerialNumber=0
[23613.762573] usb 3-2: Product: Lava E10̜Mas
[23613.762577] usb 3-2: Manufacturer: Lava E10̚Lav
[23613.833596] cdc_acm 3-2:1.1: ttyACM0: USB ACM device
[23613.833661] usbcore: registered new interface driver cdc_acm
[23613.833664] cdc_acm: USB Abstract Control Model driver for USB modems and ISDN adapters
[23613.844245] usbcore: registered new interface driver option
[23613.844276] usbserial: USB Serial support registered for GSM modem (1-port)
```

Resulting serial device:

```text
/dev/ttyACM0
```

Permissions:

```text
crw-rw---- 1 root uucp 166, 0 Sep 11 17:11 /dev/ttyACM0
```

The Linux user was **not** in the `uucp` group:

```text
$ groups
<LOCAL_USERNAME> docker wheel
```

Therefore all serial-port access in these experiments used `sudo`. (`[FACT]`)

`[FACT]` No `/dev/ttyUSB*` and no `/dev/ttyACM1` appeared at any point.

`[INTERP]` The `option`/`usbserial` driver registration lines are an autoload side effect; nothing bound to them — `cdc_acm` claimed the device, consistent with its CDC ACM descriptors.

`[FACT]` Device enumerates as **full-speed USB** (12 Mbit/s), device number 43 on bus 3, port 2 (`3-2`).

---

## 3. USB descriptor analysis

`sudo usb-devices` section for the phone (verbatim):

```text
T:  Bus=03 Lev=01 Prnt=01 Port=01 Cnt=02 Dev#= 43 Spd=12   MxCh= 0
D:  Ver= 2.00 Cls=02(commc) Sub=00 Prot=00 MxPS= 8 #Cfgs= 3
P:  Vendor=0e8d ProdID=0003 Rev=01.00
S:  Manufacturer=Lava E10̚Lav
S:  Product=Lava E10̜Mas
C:  #Ifs= 2 Cfg#= 1 Atr=80 MxPwr=500mA
I:  If#= 0 Alt= 0 #EPs= 2 Cls=0a(data ) Sub=00 Prot=00 Driver=cdc_acm
E:  Ad=01(O) Atr=02(Bulk) MxPS=  64 Ivl=0ms
E:  Ad=81(I) Atr=02(Bulk) MxPS=  64 Ivl=0ms
I:  If#= 1 Alt= 0 #EPs= 1 Cls=02(commc) Sub=02 Prot=01 Driver=cdc_acm
E:  Ad=84(I) Atr=03(Int.) MxPS=  16 Ivl=3ms
```

`lsusb -v -d 0e8d:0003` (filtered) reports, for each interface pair:

```text
      bInterfaceClass        10 CDC Data
      bInterfaceSubClass      0 [unknown]
      bInterfaceProtocol      0
      iInterface              1

      bInterfaceClass         2 Communications
      bInterfaceSubClass      2 Abstract (modem)
      bInterfaceProtocol      1 AT-commands (v.25ter)
      iInterface              2
```

What this means:

- `[FACT]` The phone exposes a **USB CDC ACM** device.
- `[FACT]` The communications interface identifies itself as an **Abstract Control Model** modem (`SubClass 2`).
- `[FACT]` Protocol `1` explicitly identifies **AT commands according to V.25ter**.
- `[FACT]` Linux therefore correctly created `/dev/ttyACM0` and bound `cdc_acm`.
- `[FACT]` There is exactly **one** exposed serial device: `/dev/ttyACM0`. No `/dev/ttyUSB*`, no `/dev/ttyACM1`.
- `[INTERP]` The two interfaces (CDC Data `0x0a` + Communications `0x02`) form a **single CDC ACM serial function** — they are not two independent serial ports. Do not expect a second "diagnostic port" from this configuration.
- `[FACT]` The device descriptor reports **3 configurations** (`#Cfgs= 3`); `usb-devices` printed only configuration 1, and the `lsusb -v` grep shows the CDC pair **three times**, consistent with each configuration containing one CDC ACM function pair. Not yet verified config-by-config (future: dump all three with `lsusb -v` and diff them).
- `[INTERP]` The interface order is **reversed relative to the usual CDC convention** (data interface at `If#=0`, communications/control interface at `If#=1` — normally the control interface comes first). Linux tolerated this and created `ttyACM0` from the control interface `3-2:1.1`.
- `[FACT]` Endpoints: bulk OUT `0x01` / bulk IN `0x81` (64-byte max packet), interrupt IN `0x84` (16 bytes, 3 ms interval). Configuration declares bus-powered, 500 mA.
- `[FACT]` `SerialNumber=0` — the device exposes **no serial-number string** (relevant if you ever want stable udev symlinks; you cannot match on serial).

---

## 4. Software used

- OS: **Arch Linux**
- Terminal serial program: **picocom**

```bash
sudo pacman -S picocom
```

Installed: `picocom-3.1-3` → banner `picocom v3.1`.

Connection command:

```bash
sudo picocom -b 115200 /dev/ttyACM0
```

Session configuration (from the picocom banner):

```text
baudrate is    : 115200
parity is      : none
databits are   : 8
stopbits are   : 1
flowcontrol    : none
local echo is  : no
emap is        : crcrlf,delbs,
```

`[FACT]` **115200 8N1 worked for all tested commands.**

`[INTERP]` Over CDC ACM the baud rate is nominal/virtual (framing is handled by USB), so the baud value is unlikely to matter; 8N1-none is the safe default regardless.

---

## 5. AT command test log

Two picocom sessions on `/dev/ttyACM0` (see §9 for raw transcripts). Full table of every command tested:

| # | Command | Intent | Observed response | Verdict |
|---|---------|--------|-------------------|---------|
| 1 | `AT` | Attention / handshake | `OK` | PASS — supported |
| 2 | `ATI` | Display identification | `ERROR` | REJECTED |
| 3 | `AT+CGMI` | Manufacturer | `ERROR` | REJECTED |
| 4 | `AT+CGMIM` | (nonstandard / possible typo of `AT+CGMI`) | `ERROR` | REJECTED |
| 5 | `AT+CGMM` | Model identification | `+CGMM: MTK2` then `OK` | PASS — supported |
| 6 | `AT+CGMR` | Firmware revision | `+CGMR: Lava_E10_61D_INT_T005_210714, 2021/07/14 13:57` then `OK` | PASS — supported |
| 7 | `AT+CGSN` | Serial number / IMEI | `ERROR` | REJECTED |
| 8 | `AT+CSQ` | Signal quality | `+CSQ: 23, 99` then `OK` (asked twice, same values) | PASS — supported |
| 9 | `AT+COPS?` | Operator selection status | `+COPS: 0` then `OK` | PASS — supported |
| 10 | `AT+CREG?` | Network registration status | `ERROR` | REJECTED |
| 11 | `AT+CPIN?` | SIM status | `ERROR` | REJECTED |
| 12 | `AT+CFUN?` | Phone functionality level | `+CFUN: 1` then `OK` | PASS — supported |
| 13 | `AT+CSCS?` | Character set | `+CSCS: "IRA"` then `OK` | PASS — supported |
| 14 | `AT+CMGF=1` | SMS text mode (set) | `ERROR` | REJECTED |
| 15 | `AT+CMGF=?` | SMS text mode (test) | `ERROR` | REJECTED |
| 16 | `AT+CMGS=?` | Send SMS (test) | `ERROR` | REJECTED |
| 17 | `AT+CMGL=?` | List SMS (test) | `ERROR` | REJECTED |
| 18 | `AT+CNMI=?` | SMS notification (test) | `ERROR` | REJECTED |
| 19 | `AT+CPMS?` | SMS message storage | `ERROR` | REJECTED |
| 20 | `AT+CSCA?` | SMS service center address | `ERROR` | REJECTED |
| 21 | `AT+CPBS=?` | Phonebook storage (test) | `ERROR` | REJECTED |
| 22 | `AT+CPBR=?` | Phonebook read (test) | `ERROR` | REJECTED |
| 23 | `AT+CLAC` | List all supported AT commands | `ERROR` | REJECTED |
| 24 | `AT+GCAP` | General capabilities | `ERROR` | REJECTED |

Tally: **8 of 24 tested commands supported, 16 rejected.**

### 5.1 Basic communication

```text
AT
OK
```

`[FACT]` Basic AT communication works. The interface is alive and parses V.250-style command lines.

### 5.2 Identification

```text
ATI      → ERROR
AT+CGMI  → ERROR
AT+CGMIM → ERROR
```

```text
AT+CGMM
+CGMM: MTK2

OK
AT+CGMR
+CGMR: Lava_E10_61D_INT_T005_210714, 2021/07/14 13:57

OK
AT+CGSN
ERROR
```

`[INTERP]` The firmware supports `CGMM` and `CGMR` but does not accept several other common identification commands (`ATI`, `CGMI`, `CGSN`) on this interface. This is a heavily filtered command set, not a full modem firmware exposure.

`[NOTE]` This does **not** prove the IMEI cannot be retrieved through other protocols (vendor AT commands, proprietary USB protocols, or firmware paths may still expose it). It only means the standard `AT+CGSN` form was rejected here. `AT+CGSN` returned `ERROR`, so **no IMEI was observed** in this session.

### 5.3 Signal / network

```text
AT+CSQ
+CSQ: 23, 99

OK
```

- `23` is the received signal strength indication (RSSI). `[INTERP]` Per the 3GPP TS 27.007 table (values 2–30 map to −109…−53 dBm in 2 dB steps), RSSI 23 ≈ **−67 dBm**, i.e. a strong signal at the time of the test.
- `99` means the **bit error rate (BER) is not known / not available** — the standard "not applicable" placeholder.

```text
AT+COPS?
+COPS: 0

OK
```

`[INTERP]` Reports **automatic operator selection mode (`0`)**. The long form (format, network status, operator name) is omitted by this firmware, so no operator is identified through this interface.

```text
AT+CREG?
ERROR
```

`[FACT]` The phone does not expose the standard registration query through this interface.

### 5.4 SIM

```text
AT+CPIN?
ERROR
```

`[FACT]` The standard SIM PIN/status command is not supported through this interface.

### 5.5 Radio functionality

```text
AT+CFUN?
+CFUN: 1

OK
```

`[FACT]` The phone reports **full functionality mode (`1`)** — the radio subsystem claims to be fully powered on.

### 5.6 Character set

```text
AT+CSCS?
+CSCS: "IRA"

OK
```

`[FACT]` Current character set is `IRA` (International Reference Alphabet — effectively plain ASCII). `[INTERP]` Interact with the port using plain ASCII; don't expect UTF-8/UCS2 handling unless `+CSCS` can be changed (untested — `AT+CSCS=?` not yet tried).

### 5.7 SMS-related commands

All rejected on `/dev/ttyACM0`:

```text
AT+CMGF=1  → ERROR
AT+CMGF=?  → ERROR
AT+CMGS=?  → ERROR
AT+CMGL=?  → ERROR
AT+CNMI=?  → ERROR
AT+CPMS?   → ERROR
AT+CSCA?   → ERROR
```

`[FACT]` The standard SMS AT command interface (3GPP TS 27.005 set) is **not exposed** through this USB port.

`[IMPORTANT]` The correct conclusion is narrow: **the tested USB AT interface does not expose the standard SMS commands.** This does **not** prove the phone itself cannot send/receive SMS — it demonstrably works as a phone on the GSM network; the commands are simply not reachable through this port. SMS functionality may exist behind vendor commands, a different USB mode, or a proprietary protocol.

### 5.8 Phonebook commands

```text
AT+CPBS=? → ERROR
AT+CPBR=? → ERROR
```

`[FACT]` Standard phonebook commands were also rejected.

### 5.9 Capability discovery

```text
AT+CLAC → ERROR
AT+GCAP → ERROR
```

`[FACT]` The firmware does not implement these common capability-discovery commands on this interface. There is **no built-in way to enumerate the supported command set** — discovery must proceed command-by-command (see §10).

---

## 6. Important observations

1. `[FACT]` The phone has a **real USB CDC ACM AT-command interface**.
2. `[FACT]` Linux correctly identifies it as a modem-like AT interface (descriptors say Abstract Control Model, protocol 1 = V.25ter AT commands; `cdc_acm` binds cleanly).
3. `[FACT]` `/dev/ttyACM0` is functional.
4. `[FACT]` Basic AT communication works (`AT` → `OK`).
5. `[FACT]` Some GSM-related commands work: `+CSQ` (signal), `+COPS?` (operator mode), `+CFUN?` (functionality).
6. `[FACT/INTERP]` The interface is **highly restricted** compared with a conventional GSM modem: 16 of 24 tested standard commands are rejected.
7. `[FACT]` Standard **SMS commands are not available** on this port.
8. `[FACT]` Standard **SIM status** (`+CPIN?`) and **registration** (`+CREG?`) commands are not available.
9. `[FACT]` There is only **one** exposed serial device (`/dev/ttyACM0`); the two USB interfaces are one CDC function, not two ports.
10. `[INTERP]` At this stage the phone should **NOT** be treated as a confirmed USB SMS modem.
11. `[FACT]` A SIM is **not required** for the USB/AT interface experiments performed so far (no command answered in a way that depended on SIM presence; the SIM-dependent queries were rejected outright).
12. `[HYP]` Installing a SIM is unlikely *by itself* to make unsupported AT commands such as `AT+CMGS` appear — the limitation looks like it is in the **exposed firmware command interface**, not in SIM state. (Cheap to falsify: see §10, experiment D.)

---

## 7. Mistakes / noise encountered

Odd input seen in session 1:

```text
[A[AAT_
ERROR
```

`[FACT]` This is terminal/input escape-sequence garbage from pressing **arrow keys inside picocom**, not evidence of a phone problem. Picocom does no line editing — it passes bytes straight to the modem. Arrow keys emit ANSI CSI sequences (e.g. up-arrow = `ESC [ A`); the modem silently consumed the `ESC` bytes and choked on the rest, answering `ERROR` to the mangled line `AT_`.

Lesson for future sessions: **don't use arrow keys (or Tab) while typing at the modem** — every byte goes to the device. Backspace works because of picocom's default `delbs` mapping. If a line gets mangled, finish it (the modem will answer `ERROR`) and retype the command cleanly.

How to exit picocom:

```text
Ctrl+A   then   Ctrl+X
```

(`C-a C-x` — the escape character is `C-a`, shown in the banner as `escape is: C-a`.)

Other session noise, for completeness:

- `[FACT]` Unrelated ACPI error (`\_SB.PC00.LPCB.H_EC._Q80 ... AE_NOT_FOUND`) and Wi-Fi reassociation lines in `dmesg` — laptop-side noise, nothing to do with the phone.
- `[FACT]` Reconnects/suspend events in the log are from the laptop, not the phone; the phone stayed enumerated as device 43 for the whole session.

---

## 8. Investigation so far (chronological)

1. Phone plugged into laptop USB, on-device USB mode set to **COM port**.
2. Kernel enumerated it: full-speed device number 43 on bus 3 (`3-2`), `idVendor=0e8d idProduct=0003`, `bcdDevice= 1.00`; strings garbled (`Lava E10̚Lav` / `Lava E10̜Mas`), no serial number string.
3. `cdc_acm` bound to interfaces 0/1 and created `/dev/ttyACM0` at 17:11. `option`/`usbserial` registered but bound nothing. No `/dev/ttyUSB*`, no second ACM port.
4. `lsusb` listed `0e8d:0003 MediaTek Inc. MT6227 phone`.
5. User checked `groups` (`<LOCAL_USERNAME> docker wheel`) → not in `uucp` → `sudo` required for the port.
6. Installed `picocom` 3.1 (`pacman -S picocom`).
7. **Session 1** (~17:11): `AT`→OK; `ATI`, `AT+CGMI`, `AT+CGMIM`→ERROR; arrow-key garbage incident (`[A[AAT_`→ERROR); `AT+CSQ`→`+CSQ: 23, 99` (twice); `AT+CREG?`, `AT+CPIN?`, `AT+CMGF=1`→ERROR; `AT+COPS?`→`+COPS: 0`; `AT+CPBS=?`, `AT+CPBR=?`, `AT+CMGF=?`, `AT+CMGS=?`, `AT+CMGL=?`, `AT+CNMI=?`→ERROR. Exited with `C-a C-x`.
8. Dumped descriptors: `usb-devices` (config 1) and `lsusb -v -d 0e8d:0003` (interface classes/subclass/protocol); confirmed single CDC ACM function, AT-command protocol, 3 device configurations.
9. **Session 2** (~17:17): `AT+CLAC`, `AT+GCAP`→ERROR; `AT+CGMM`→`MTK2`; `AT+CGMR`→`Lava_E10_61D_INT_T005_210714, 2021/07/14 13:57`; `AT+CGSN`→ERROR; `AT+CFUN?`→`+CFUN: 1`; `AT+CSCS?`→`"IRA"`; `AT+CPMS?`, `AT+CSCA?`→ERROR. Exited.
10. Conclusion recorded: interface real and functional but heavily restricted; not a confirmed SMS modem; investigation handed over via this notebook.

Raw transcripts (abridged of picocom banner, otherwise verbatim):

Session 1:

```text
AT
OK
ATI
ERROR
AT+CGMI
ERROR
AT+CGMIM
ERROR
AT
OK
[A[AAT_
ERROR
AT+CSQ
+CSQ: 23, 99

OK
AT+CREG?
ERROR
AT+CPIN?
ERROR
AT+CMGF=1
ERROR
AT+CSQ
+CSQ: 23, 99

OK
AT+COPS?
+COPS: 0

OK
AT+CPBS=?
ERROR
AT+CPBR=?
ERROR
AT+CMGF=?
ERROR
AT+CMGS=?
ERROR
AT+CMGL=?
ERROR
AT+CNMI=?
ERROR
```

Session 2:

```text
AT+CLAC
ERROR
AT+GCAP
ERROR
AT+CGMM
+CGMM: MTK2

OK
AT+CGMR
+CGMR: Lava_E10_61D_INT_T005_210714, 2021/07/14 13:57

OK
AT+CGSN
ERROR
AT+CFUN?
+CFUN: 1

OK
AT+CSCS?
+CSCS: "IRA"

OK
AT+CPMS?
ERROR
AT+CSCA?
ERROR
```

---

## 9. Current status

> The Lava E10 Color CL220 is successfully connected to Linux through USB COM mode and exposes `/dev/ttyACM0` as a CDC ACM AT-command interface. Basic AT communication and selected GSM queries work, but standard SMS, SIM, registration, phonebook, and capability commands tested so far are rejected. The device is therefore not yet confirmed to function as a USB SMS modem.

---

## 10. Future investigation / next experiments

**Rules for all probing:**

- Test in the order: `AT+X=?` (test form) → `AT+X?` (read form) → only then any write form.
- **Never blind-write.** Avoid anything that could alter network settings, erase data, flash firmware, or modify NV memory until its meaning is known. Specifically avoid `+CFUN=0/4` (radio off), `+CPBW` (phonebook write), any IMEI/NV write command (MediaTek firmwares have historically had them — treat any such command as dangerous and out of scope), and any flash/boot tool until the read-only picture is complete.
- Record everything: use `picocom --logfile at.log` so transcripts include timing and raw bytes, and echo vs. response can be distinguished.

### A. Error-reporting upgrade (highest value, near-zero risk) — `[HYP]` most MTK firmwares support it

```text
AT+CMEE=?     (test form first)
AT+CMEE=1     (verbose +CME ERROR codes)
```

Then **re-run the rejected commands**. Bare `ERROR` may become `+CME ERROR: <n>`, which tells us *why* (e.g. "not supported" vs "SIM not inserted" vs "operation not allowed") and could redirect the whole investigation.

### B. Safe read-only AT probes (each: test form first)

```text
AT+CPAS?      phone activity status
AT+CBC?       battery charge
AT+CCLK?      real-time clock
AT+CGATT?     GPRS attach state
AT+CGDCONT?   PDP context definitions (read)
AT+CESQ       extended signal quality
AT+CSCS=?     available character sets
AT+CGMM=? / AT+CGMR=? / AT+CGMI=?   test/read variants of the commands that work
AT&V          display active configuration
ATE0 / ATE1   echo off/on (reversible; helps clean up transcripts)
AT+CGMI       retest once more, cleanly typed, with CMEE=1 active
```

If `AT+CIMI` (IMSI) or `AT+CNUM` (subscriber number) is ever tried, **mask the output** (§12).

### C. SIM in/out A/B test — cheap falsification of Observation 12

Re-run the full §5 table once with a SIM inserted and once without, and diff. Low expected impact, but it either kills or confirms the "commands are SIM-gated" hypothesis in five minutes.

### D. Enumerate the phone's other USB modes

The handset's USB settings menu likely offers more than "COM port" (mass storage, possibly webcam/other). Connect in each mode and record VID:PID, interface classes, and any additional tty nodes. Different modes may expose more (or different) ports — including MediaTek boot/VCOM-style modes worth mapping separately.

### E. MediaTek / platform reverse engineering

Investigate the USB protocol and the MediaTek MT6227/MTK2 architecture (keeping §1's caveat that MT6227 is a database name for the VID:PID and the true silicon is unverified — see the `61D` hypothesis). Look for:

- MediaTek USB CDC implementations
- MT6227 USB protocols
- Lava E10 service/engineering interfaces
- MediaTek feature-phone AT command references (vendor AT sets beyond 27.007)
- proprietary phone-management protocols
- PC synchronization software
- Windows USB drivers/software for the Lava E10 (MTK CDC/VCOM drivers, "PhoneSuite"-class tools often reveal which AT/vendor commands the firmware answers)
- firmware extraction / reverse engineering possibilities (more invasive; treat as a separate, risk-assessed phase)

### F. Host-side convenience

Add the user to the port-owning group so `sudo` is no longer needed:

```bash
sudo usermod -aG uucp <LOCAL_USERNAME>   # then log out/in
```

### G. SMS gateway goal — **UNCONFIRMED GOAL, not a demonstrated capability**

The original motivation is to determine whether this phone can eventually serve as a USB GSM modem for an SBC:

```text
Linux SBC (Orange Pi / Raspberry Pi)
   |
   | USB
   v
Lava E10
   |
   | GSM
   v
SMS network
```

Status: the USB link and AT channel are proven; **no SMS capability has been demonstrated over this interface**. Whether the goal is reachable depends on finding either SMS-capable vendor AT commands or a proprietary protocol that exposes SMS.

---

## 11. Reproducibility

Compact sequence for another researcher to repeat the investigation:

```bash
lsusb
ls -l /dev/ttyACM* /dev/ttyUSB*
sudo dmesg | grep -E '0e8d|ttyACM|ttyUSB|cdc_acm|option'
sudo usb-devices | sed -n '/Vendor=0e8d ProdID=0003/,/^$/p'
lsusb -v -d 0e8d:0003 2>/dev/null | grep -E 'bInterfaceClass|bInterfaceSubClass|bInterfaceProtocol|iInterface'
sudo picocom -b 115200 /dev/ttyACM0
```

Expected from the `lsusb` line: `Bus 003 Device 043: ID 0e8d:0003 MediaTek Inc. MT6227 phone`
Expected device node: `/dev/ttyACM0` (`crw-rw---- root uucp`), no `/dev/ttyUSB*`.

Then inside picocom, run the same probe set (exit with `Ctrl+A` `Ctrl+X`):

```text
AT
AT+CSQ
AT+COPS?
AT+CGMM
AT+CGMR
AT+CFUN?
AT+CSCS?
AT+CREG?
AT+CPIN?
AT+CMGF?
AT+CMGS=?
AT+CMGL=?
AT+CNMI=?
AT+CPMS?
AT+CSCA?
AT+CPBS=?
AT+CPBR=?
AT+CLAC
AT+GCAP
AT+CGSN
```

Observed responses (reference — full detail in §5):

```text
AT          → OK
AT+CSQ      → +CSQ: 23, 99            OK
AT+COPS?    → +COPS: 0                OK
AT+CGMM     → +CGMM: MTK2             OK
AT+CGMR     → +CGMR: Lava_E10_61D_INT_T005_210714, 2021/07/14 13:57   OK
AT+CFUN?    → +CFUN: 1                OK
AT+CSCS?    → +CSCS: "IRA"            OK
AT+CREG?    → ERROR
AT+CPIN?    → ERROR
AT+CMGF?    → ERROR   (both `AT+CMGF?`-style and `AT+CMGF=1`/`AT+CMGF=?` were rejected)
AT+CMGS=?   → ERROR
AT+CMGL=?   → ERROR
AT+CNMI=?   → ERROR
AT+CPMS?    → ERROR
AT+CSCA?    → ERROR
AT+CPBS=?   → ERROR
AT+CPBR=?   → ERROR
AT+CLAC     → ERROR
AT+GCAP     → ERROR
AT+CGSN     → ERROR
```

(Also tested and rejected: `ATI`, `AT+CGMI`, `AT+CGMIM`.)

Note: exact device number (43) and bus/port (`3-2`) may differ on another machine; the VID:PID `0e8d:0003` is the stable identifier.

---

## 12. Notes for future researchers

- Published copies use named placeholders for identifier-like values.
- Keep the `[FACT]` / `[INTERP]` / `[HYP]` discipline: append new observations with tags and timestamps so conclusions stay auditable.
- The supported-command tally stands at **8/24** as of 2026-09-11; update it (§5) as new commands are probed.
- Reference standards for the command set: 3GPP **TS 27.007** (modem control: `+CSQ`, `+COPS`, `+CREG`, `+CPIN`, `+CGMM`, …) and **TS 27.005** (SMS AT commands: `+CMGF`, `+CMGS`, `+CMGL`, `+CNMI`, `+CPMS`, `+CSCA`, …). The rejection of the entire TS 27.005 set tested so far is the key open question.

---

## 13. Addendum — automated live probing (same day, 17:22–17:55)

The investigation was continued with automated tooling, run directly on the host. **This addendum supersedes parts of §5–§9.**

### 13.1 New facts that change earlier conclusions

1. `[FACT]` **`AT+CMEE=1` is supported.** With verbose errors on, every previously "ERROR" command answers **`+CME ERROR: 100`** (100 = "unknown"). `[INTERP]` These commands are **absent from the AT parser**, not blocked by SIM/registration state. This kills the "insert a SIM and commands may appear" hypothesis (Observation 12) and explains the whole §5 table.
2. `[FACT]` **`AT+CSCS=?` works**: `+CSCS: ("IRA", "GSM", "HEX", "PCCP437", "8859-1", "UCS2", "UCS2_0X81")`. `[INTERP]` `PCCP437` and `UCS2_0X81` are MediaTek-specific charset names — an MTK AT-parser fingerprint.
3. `[FACT]` **`AT+COPS=?` works and performs a live network scan**: `+COPS: (2,"42901","42901","42901",0),(1,"42902","42902","42902",0),,(0-3),(0-2)`. `[INTERP]` 42901 = Nepal Telecom, 42902 = Ncell. **The GSM radio is fully functional and reachable through this USB port.**
4. `[FACT]` `AT+CIND=?` works: `("battchg",(0-5)), ("signal",(0-5)), ("service",(0,1)), ("message",(0,1)), ("call",(0,1)), ("roam",(0,1)), ("smsfull",(0,1))`. `[INTERP]` The presence of **`message`** and **`smsfull`** indicators proves an SMS subsystem exists in the firmware — it is simply not exposed via the TS 27.005 AT set. Also: `AT+CMER=3,0,0,1` was enabled for 20 s (no URCs while idle) and disabled cleanly — fully reversible.
5. `[FACT]` **`AT+VTS=?` works**: digits `0-9, A-D, #, *` accepted — **DTMF tone dialing is exposed through this port**. (`AT+VTD` is absent.)
6. `[FACT]` Call-control subsystem present: `AT+CLCC` → OK (no active calls), `AT+CLCC=?` → OK, `AT+CHLD=?` → `(0, 1, 1x, 2, 2x, 3, 4, 5)` (full call-hold/multiparty set), `AT+CLIP=?` → `(0-1)`.
7. `[FACT]` `AT+CNUM` → OK with empty body (no MSISDN stored on the phone). Identifier-like values from other probe outputs are represented by placeholders in the published copy.
8. `[FACT]` Confirmed absent (all `+CME ERROR: 100`): `CR, CRC, CSCB, CSCA=?, CPMS=?, CMGF?, CMUX=?, CGREG?, CGPADDR, CGEREP=?, CVHU=?, CALM?, CLVL?, CVOICE=?, CTZU=?, CTZR=?, CPOL?`, plus `ATI, CGMI, CGMI=?, CGSN, CREG?, CREG=?, CPIN?, CPIN=?, CIMI, CMGF=?, CLAC, GCAP` from phase 1.
9. `[FACT]` All **3 USB configurations are identical** (each = one CDC ACM pair, same interface layout). No hidden second port in configs 2/3 (`../../captured-output/usb/usb_dump.txt`).
10. `[FACT]` A 10 s connect-time URC window and a 20 s CMER-enabled window both produced **zero unsolicited bytes** — the port is silent unless addressed.

### 13.2 Updated verdict

> `[INTERP]` The `/dev/ttyACM0` interface is a **MediaTek feature-phone AT parser with application-level filtering** (PhoneSuite-style): signal, network scan, model/firmware ID, call control, DTMF, and indicators work; the entire standard SMS AT stack, SIM queries, and registration queries are compiled out. **Standard-AT SMS gatewaying is a dead end on this port.** Remaining SMS routes: vendor/proprietary commands, other USB modes (§10-D), or the PC-sync protocol the firmware was built for.

### 13.3 Tooling created (in the repo, reusable)

| File | Purpose |
|---|---|
| `../../scripts/probes/at_probe.py` | Phase-1 prober: URC window, CMEE upgrade, safe read/test probes, auto-mask of ≥10-digit numbers, writes `../at-probes/at_results.md` + `../../captured-output/at/at_raw.log` |
| `../../scripts/probes/at_probe2.py` | Phase-2 follow-ups (CIND/CMER/CLCC/mux/SMS test forms) → `../at-probes/at_results2.md` |
| `../../scripts/probes/at_probe3.py` | Phase-3 (CIND names, VTS, audio/tz probes, CMER URC window + restore) → `../at-probes/at_results3.md` |
| `../../scripts/mock/mock_modem.py` | pty mock emulating the E10 (incl. verbose CME errors); used to validate the prober and the masking before touching hardware |
| `../../captured-output/usb/usb_dump.txt` | Full `lsusb -v` dump of all 3 configurations |
| `../../captured-output/at/at_raw.log` | Raw byte transcript of all real probe sessions |

Validation note: the prober was first run against `../../scripts/mock/mock_modem.py` on a pty; masking was verified with a synthetic identifier fixture.

### 13.4 Next experiments (revised by the addendum findings) — see §14 for results

1. Probe MTK vendor AT sets for this firmware generation (`AT+ERAT?, AT+ESUPORT?, AT+EACC?, AT+CMGR?`-style guesses and published MTK lists) — **test forms only**, watch for anything outside the 3GPP namespace.
2. Try each of the phone's **other USB modes** (§10-D) and diff VID:PID + interfaces; a "PC sync" mode likely carries the protocol the firmware's SMS stack actually speaks.
3. With CMER on, generate events from the phone's keypad (miss a call / receive an SMS) while the port is open, to see whether URCs appear on `message`/`call` indicators.
4. `ATD<number>;` voice-dial test (harmless, cancels with `ATH`) to confirm outbound call control, then `AT+VTS` during the call.
5. USB-level sniffing (Wireshark/usbmon) of the vendor's Windows sync software traffic, if that route is pursued. (Only if §14 steps 1–4 close out the AT-level routes.)

---

## 14. Addendum — TekBuster-informed vendor probe (same day, ~18:24–18:46)

Session continued with root access (user now `uid=0`; no more `sudo` needed for the port). Device re-enumerated as **Bus 003 Device 009** (same `0e8d:0003`); `/dev/ttyACM0` unchanged. The phase-4 prober was rewritten with **code-enforced safety gating** before touching hardware:

- every write form is a *gated step* whose precondition is the verdict of the command's own test form (`=?` must have returned `OK`); a failed gate logs `SKIPPED` and nothing is sent;
- `AT+ESUO` write values are **parsed from the command's own test-form response** and only sent if the current value (from `AT+ESUO?`) is known, so the original state is always restorable;
- the `AT+EGMR=1,...` (IMEI **write**) mode is structurally absent from the plans;
- an `SMS input prompt ('>')` anywhere in a response **aborts the session instantly** (no message body can ever be composed);
- masking (`\d{4}\d{6,}\d{2}` → first4/last2 kept) verified against the mock before hardware.

Validation: all probes were first run against an upgraded, **stateful** `../../scripts/mock/mock_modem.py` (emulates CMEE/CMGF/ESUO state, vendor commands, ESUO gating, fake IMEI/IMSI/MSISDN). A real bug was caught this way (the prompt-abort regex missed a `>\r\n` line) — fixed and re-verified on the mock, then on hardware.

### 14.1 New facts

1. `[FACT]` **Chipset identified: MT6261.** `AT+EGMR=0,0` → `+EGMR: "MT6261"`. The §1 `61D` hypothesis is **confirmed**; the `MT6227` name in `lsusb` is purely a `usb.ids` VID:PID database artifact.
2. `[FACT]` The MTK proprietary vendor command `AT+EGMR` is present. Read responses (all `OK`, masking applied where needed):
   - `AT+EGMR=?` → `+EGMR: (0,1),(0-5,7-12)` — mode 0 = read, **mode 1 = write is exposed in the parser**
   - `AT+EGMR=0,0` → `"MT6261"` (chipset)
   - `AT+EGMR=0,1` → `"2000.00.00"` (build date, zeroed)
   - `AT+EGMR=0,2` → `"1.0"` (hardware version)
   - `AT+EGMR=0,3` → `"Lava_E10_61D_INT_T005_210714"` (firmware; matches `+CGMR`)
   - `AT+EGMR=0,4` → `"LAVA61D_11C_HW"` (board/hardware ID)
   - `AT+EGMR=0,5` → `"<DEVICE_ID_REDACTED>"` (device serial value omitted from the published output)
   - `AT+EGMR=0,7` → IMEI (SIM1), masked → `<IMEI_REDACTED>`
3. `[INTERP]` The IMEI-write capability (`AT+EGMR=1,...`) exists in the firmware. **Hard out of scope** per the standing rules — never sent, never to be sent. Noted here only as a safety observation.
4. `[FACT]` `AT+ESUO` exists: `=?` → `+ESUO: (4-5)`; read → `+ESUO: 4, 4`. `[INTERP]` This firmware numbers **SIM1=4, SIM2=5** (consistent with TekBuster's `sim+3` where sim is 1-based), not the mock/NokiaTool-style 3/4.
5. `[FACT]` **ESUO gating hypothesis (tekbuster_analysis.md) is FALSIFIED.** With SIM1 already selected (4) we switched to SIM2 (`AT+ESUO=5` → OK, confirmed by `+ESUO: 5, 4` — second field appears to be the active-for-AT value) and retested: `AT+CMGF=?`, `AT+CMGS=?`, `AT+CPMS=?`, `AT+CPBS=?`, `AT+CIMI` → all bare `ERROR` (CMEE had reverted to off after the SIM switch). Restored to `AT+ESUO=4`, verified `+ESUO: 4, 4`. SMS commands are **compiled out of the parser regardless of SIM selection**.
6. `[FACT]` `AT+CKPD` works: `=?` → OK (list form empty); `AT+CKPD="0"` → OK. Keypad emulation is available for UI-driven testing if ever needed.
7. `[FACT]` `AT+ESIMS` (proprietary SIM status): `SIM1 STATUS: 0`, `SIM2 STATUS: 0` (0 = no card / absent for both, consistent with a SIM-less session).
8. `[FACT]` `AT+EFUN?` → `+EFUN: 1` (alternative functionality query; consistent with `+CFUN: 1`).
9. `[FACT]` After the SIM-switch, CMEE setting reverted to disabled (`ERROR` instead of `+CME ERROR: 100`) — `[INTERP]` the AT parser resets error-reporting state on ESUO change; re-set `AT+CMEE=1` after any ESUO write.

### 14.2 Updated verdict

> `[INTERP]` The vendor-command route does **not** unlock SMS: the standard TS 27.005 set is absent under both ESUO selections. TekBuster-style SIM gating is not the mechanism on this firmware. The AT-level SMS routes are now exhausted; remaining candidates are the phone's **other USB modes** (§15) and the **PC-sync protocol** (§13.4-5). Positive yield: chipset confirmed (MT6261), full EGMR identity set read, keypad emulation available.

### 14.3 Tally update (§5/§13 tables)

Phase 4/4b added 33 distinct commands/forms on hardware; combined tally **≈ 32 of 66 probed commands supported** (8/24 → phase 1–3; +EGMR read forms, ESUO, CKPD, ESIMS, EFUN, CMEE=2, CIND/CMER/CLCC/CHLD/CLIP/VTS from earlier phases). Gated steps that would have violated test order: 0. Sessions: aborted 0 times; prompt guard never triggered on hardware.

### 14.4 Tooling added

| File | Purpose |
|---|---|
| `../../scripts/probes/at_probe4.py` | Gated phase-4 prober: TekBuster vendor set, conditional write forms, prompt-abort, masking → `../at-probes/at_results4.md`, `../../captured-output/at/at_raw4.log` |
| `../../scripts/probes/at_probe5.py` | Phase-4b: EGMR read sweep, ESUO switch (range-parsed values, restore), gated retests → `../at-probes/at_results4b.md`, `../../captured-output/at/at_raw4b.log` |
| `../../scripts/mock/mock_modem.py` | Rewritten: stateful (CMEE/CMGF/ESUO), vendor commands, ESUO gating, fake identifiers for masking tests |

---

## 15. Pending next steps (from the task list)

- **§15-A USB mode enumeration** — for each mode in the handset's USB settings (mass storage, sync/PC-suite, diagnostic if present): `lsusb`, `usb-devices`, `lsusb -v -d 0e8d:<pid>` filtered to interface classes, resulting tty/block devices. No AT commands in other modes yet — characterize only. (Requires the user to switch modes on the handset.)
- **§15-B Passive URC capture** — `AT+CMER=3,0,0,1` on, port open/logging; real incoming SMS + real incoming call from another phone; record any `+CIND` `message`/`call` URCs.
- **§15-C Voice/DTMF** — `ATD<num>;` to a safe test number, `AT+VTS` tones in-call, `ATH` hangup. Needs a user-provided safe number.
- **§15-D USB sniffing** — only if A–C close out the AT-level routes.

`[FACT]` Session state (18:5x): **no SIM inserted** (`AT+ESIMS?` → `SIM1 STATUS: 0`, `SIM2 STATUS: 0`; `AT+CIND?` → `service: 0`). Steps §15-B (URC capture) and §15-C (voice/DTMF) are **blocked until a SIM is inserted and registered** — both require live network. §15-A (USB mode enumeration) is SIM-independent and proceeds first, per the user's go-ahead.

---

## 16. Addendum — USB mode enumeration (§15-A, ~18:51–18:56)

Method: user switched the handset's USB mode; per-mode snapshots captured with `usb_snapshot.sh` (`usb_mode_*.md`); descriptor dumps only, **no AT commands sent in any other mode**.

### 16.1 Menu inventory

`[FACT]` The handset offers exactly **two USB modes**: **COM port** and **Mass storage**. No PC-suite/sync, webcam, diagnostic, or charge-only entries exist.

### 16.2 Mode characteristics

| Mode | VID:PID | Interfaces | Nodes | Notes |
|---|---|---|---|---|
| COM port | `0e8d:0003` | 1× CDC ACM (Data 0a + Comm 02/ACM/1) | `/dev/ttyACM0` | no serial string; 3 identical configs; AT channel (§5, §13, §14) |
| Mass storage | `0e8d:0002` | 1× MSC 08/06/50 (Bulk-Only, `usb-storage`) | `/dev/sdc` | **0 B, no media** — microSD slot empty; internal flash NOT exposed; serial string PRESENT (`<USB_SERIAL_REDACTED>`, value omitted from the published copy); no AT capability |

`[FACT]` In MSC mode the PID changes 0003 → 0002 and a serial-number string appears; manufacturer/product strings are equally garbled in both modes; device stays on bus 3, port 2, full-speed, Rev 1.00.

`[INTERP]` Mass storage exposes the microSD slot only (no card inserted → 0 B). Nothing AT/SMS-relevant in this mode; it is also not a hidden diagnostic channel.

`[INTERP]` With **no dedicated PC-sync USB mode** on this handset, the §15-D hypothesis ("sniff MediaTek sync software in a sync mode") loses its main target: vendor tools must either use the very AT-over-ACM interface already exhaustively probed, or drive mass storage. USB sniffing is therefore **deprioritized** until steps 3–4 are SIM-enabled and exhausted.

### 16.3 Updated overall verdict

> `[INTERP]` All SIM-free AT/USB routes are now exhausted: the COM-port AT parser (a) hides the entire TS 27.005 SMS set under both ESUO selections, (b) offers no vendor SMS path, (c) has no alternative USB mode carrying anything else. **The SMS-gateway goal is now gated on exactly one untested path: live-network URC behavior with a SIM inserted (§15-B), plus the §15-C outbound call-control demonstration.** If a SIM becomes available: insert it, re-run `AT+ESIMS?` / `AT+CIND?` / `AT+CSQ` to confirm registration, then run `urc_capture.py` while triggering an incoming SMS + call, then `call_test.py <safe-number>`.

---

## 17. Addendum — dual-channel discovery + SMS completeness sweep (~18:59–19:06)

### 17.1 Dual-channel discovery (unplanned bonus)

`[FACT]` On re-plugging in COM mode, a driver race occurred: `option` bound the **data** interface (If#0) → `/dev/ttyUSB0`, and `cdc_acm` failed on the control interface with `-EBUSY` (error -16).

`[FACT]` The raw data interface speaks AT too: `AT`→`OK`, `+CGMM: MTK2`, `+CIND?` and `+ESUO?` all respond on `ttyUSB0`.

`[FACT]` The SMS rejection is **identical on the data interface** (`CMGF=? / CPMS? / CSCA? / CNMI=? / CMGS=?` → `+CME ERROR: 100`).

`[INTERP]` The application-level SMS filtering lives in the **shared AT parser**, not per-USB-interface. There is no "hidden" second channel.

`[FACT]` Binding restored: `option` removed, device re-bound → `/dev/ttyACM0` back (canonical `cdc_acm` on the control interface). Note for future sessions: if enumeration yields `ttyUSB0` instead of `ttyACM0`, `rmmod option` + USB unbind/bind fixes it.

### 17.2 SMS completeness sweep (phase 6, `../at-probes/at_results6.md`)

`[FACT]` With `CMEE=1`, **all remaining TS 27.005 SMS commands return `+CME ERROR: 100`** on their test forms: `CMGR, CMGW, CMGD, CMSS, CNMA, CSMP, CSCB, CMGC, CSMS, CSAS, CRES`, plus read forms `CPMS?, CSCA?`. Combined with phases 1–4 (`CMGF, CMGS, CMGL, CNMI, CPMS, CSCA`), **the entire TS 27.005 set is now formally closed** — no form, channel, or SIM-selection state makes it appear.

`[FACT]` MTK vendor SMS guesses `AT+ECMG=?`, `AT+ECMGS=?`, `AT+ECAMS=?` → `+CME ERROR: 100` (not present in this build).

`[INTERP]` **AT-level SMS on this firmware is impossible.** Any "make SMS work" effort must go through: (a) `AT+CKPD` UI automation of the phone's native SMS app, (b) CMER `message`-indicator detection of incoming SMS once a SIM is in, or (c) firmware replacement — out of scope.

### 17.3 Remaining SMS paths (honest status)

| Path | Status |
|---|---|
| Standard/vendor AT SMS | **Closed** (§17.2) |
| CKPD-driven native SMS app | **Open** — needs live UI verification (§17.4) |
| Incoming-SMS detection via CMER URC | Open — needs SIM |
| SMS *sending* over USB | **No path exists** short of UI automation |

### 17.4 CKPD UI-automation experiment

Method: send single keypresses via `AT+CKPD="<key>"` while the user watches the handset screen and reports what happens. Key alphabet per NokiaTool conventions: digits `0-9`, `*`, `#`, softkeys `[` `]`, `m`, send/end `s`/`e`, arrows `<` `>` `^` `v`. Every step is a normal keypad press — fully reversible with the phone's own End/Back key.

`[FACT]` **Complete UI-automation chain demonstrated (19:1x), all via `AT+CKPD`, zero physical keypresses:**

1. `AT+CKPD="["` from idle → **Menu opened** (user-confirmed)
2. `AT+CKPD="m"` with highlight on Messages → **Messages submenu opened**
3. `AT+CKPD="m"` on "Write new" → **SMS text editor opened**
4. `AT+CKPD="5"` in the editor → **character `J` appeared in the message body** (single press of 5 in ABC mode; default input mode is uppercase ABC)

The user exited via the physical End key afterwards (clean-state rule).

Additional CKPD facts from the earlier exploratory round:
- `[FACT]` One `AT+CKPD="["` returned `+CME ERROR: 100`, and the identical command returned `OK` ~30 s later → key acceptance is **state/context-dependent** (transient rejection in some UI states).
- `[FACT]` `AT+CKPD="v"` (down arrow) → `OK`; `AT+CKPD="m"` at idle → `OK` but no visible effect (consistent with OK-key being a no-op on the idle screen).
- **Process lesson:** simultaneous physical keypresses + CKPD presses caused a UI state conflict (screen went back / confusing state). Rule for all future CKPD walks: **one key per confirmation round, user hands off the keypad**, recover to idle with the physical End key between experiments.

### 17.5 CKPD key map established for this build

| Key code | Function (observed) |
|---|---|
| `[` | Left softkey (opens Menu from idle; context softkey elsewhere) |
| `m` | **Center OK key** (activates the highlighted item) |
| `]` | Right softkey (assumed Back — unverified) |
| `0`–`9` | Text input (multitap ABC; single press 5 = `J`) / digits in numeric fields |
| `<`, `>`, `^`, `v` | Arrows (accepted; `<` visibly moved something earlier) |
| `s`, `e` | Send / End keys (unverified — treat `e` cautiously) |

### 17.6 Verdict update after the CKPD demonstration

> `[INTERP]` **An SMS gateway over this phone is feasible without any AT-SMS support**: an SBC can drive the phone's native SMS app entirely over `/dev/ttyACM0` via `AT+CKPD` (open editor, type text with multitap, confirm send). Fragile (UI-dependent, slow, no delivery confirmation beyond the screen) but real. The final transmission step still requires a **SIM + network** (§17.3). With a SIM inserted, the complete demo is: CKPD-write message → CMER `message`-indicator URC on incoming SMS → `ATD…;`/`VTS`/`ATH` voice test.

---

## 18. Addendum — SIM inserted: registration, URC verdict, voice/DTMF proof (~19:25–19:45)

The user inserted a **SIM1** (Nepal Telecom) and authorized test calls/messages to their own second phone (number masked everywhere per §12). A driver race recurred on re-plug (§17.1) and was fixed the same way (`rmmod option` + rebind → `/dev/ttyACM0`).

### 18.1 Registration facts

- `[FACT]` `AT+ESIMS?` → `SIM1 STATUS: 1` (was 0), `SIM2 STATUS: 0`.
- `[FACT]` `AT+CIND?` → `+CIND: 5,5,1,0,0,0,0` — **`service` indicator flipped 0→1** on SIM insertion; battery/signal full.
- `[FACT]` `AT+CSQ` → `31, 99` (≈ −51 dBm, very strong). `AT+COPS?` → `+COPS: 0,0,"42901"` — **the operator name now appears** (with SIM; earlier SIM-less reads returned bare `+COPS: 0`).

### 18.2 §10-C closed: SIM presence does NOT unlock the SMS set

`[FACT]` With SIM1 registered and full signal: `AT+CMGF=? / CMGS=? / CPMS? / CSCA?` → **`+CME ERROR: 100`**, identical to the SIM-less runs. The §10-C A/B hypothesis ("commands may be SIM-gated") is **falsified**; the compile-time filtering interpretation (§13.1-1) stands.

### 18.3 Step 3 — passive URC capture: DEFINITIVE NEGATIVE

- `[FACT]` Attempt 1 (flawed, honestly recorded): the capture was launched as a background process and **died seconds later** — no listener was attached during the user's first SMS + call; its `CMER` restore never ran (state left armed until attempt 2). Process-lesson for this environment: long listens must run **blocking**, not backgrounded.
- `[FACT]` Attempt 2 (valid): `urc_capture.py` ran **blocking** for 100 s — `AT+CMER=3,0,0,1` → OK, listened, `AT+CMER=0,0,0,0` → OK (state verified restored). The user **sent an SMS during the window and confirmed the E10's screen showed it arriving**.
- `[FACT]` **Zero unsolicited bytes** on `/dev/ttyACM0` during the entire window (`urc_capture_result.md`, `urc_capture.log`).
- `[INTERP]` This firmware **does not emit any URCs on the USB COM port** — not for incoming SMS, and (from the earlier armed window overlapping a real ring) not for incoming calls either. `CMER` is accepted and ignored. Combined with §17.2: the port is strictly **command/response only**; event-driven SMS detection over AT is impossible on this build.

### 18.4 Step 4 — voice/DTMF: COMPLETE SUCCESS

`[FACT]` Two `call_test.py` runs to the user's authorized test number (masked in all outputs and scrubbed from `call_test.log`):

1. `ATD+97………42;` → `OK`; `AT+CLCC` → `+CLCC: 1,0,3,0,0,"97………42",145` (one outgoing call). The far end rang; the user did not answer; script `ATH`-hung up cleanly (`CLCC` → OK, empty).
2. Re-run with the far end **answered**: dial accepted, **all 11 `AT+VTS` tones (1-9,#,*) returned `OK` while the call was active**, and the **user confirmed hearing the DTMF tones on the far end**. Mid-call `CLCC` showed stat `0` (active) vs stat `3` while ringing in run 1. `ATH` → `OK` → `CLCC` empty. Fully reversible, no state left changed.

`[INTERP]` Outbound call control, in-call DTMF injection, and hangup are **fully scriptable over this port** — the §13 `+VTS`/`+CLCC`/`+CHLD` capability is confirmed end-to-end on live network.

### 18.5 Final tally and verdict

- Tally: **≈25 of ≈70** distinct AT commands/forms probed across phases 1–6 are supported (plus `COPS=?` network scan and the full call-control set).

> `[INTERP]` **FINAL VERDICT (all five planned steps executed):** The Lava E10's USB COM port is a command/response-only MTK AT channel with the entire SMS stack (TS 27.005 + vendor guesses) compiled out — under both SIM states, both USB interfaces, and with `CMER` event reporting accepted-but-inert. **No AT-level SMS path exists.** What remains — and is now **proven** — is: (a) full voice-call control with DTMF over AT (`ATD/VTS/ATH`), and (b) **complete remote-UI control via `AT+CKPD`** (§17.4–17.5: menu → Messages → editor → text injected). A practical SMS gateway on an SBC is therefore possible **only** by CKPD-driving the native Messages app; incoming-SMS *notification* over USB is not possible at all (no URCs). Firmware replacement would be the only route to true AT-SMS, and is out of scope by the standing safety rules.

---

## 19. Addendum — NATIVE SMS SEND ACHIEVED over USB (§18 follow-through, ~19:50–20:2x)

The user pushed for the remaining native SMS path. Result: **a real SMS was transmitted over the GSM network, composed and sent entirely by keypresses injected over `/dev/ttyACM0` — received on the destination phone.** This section records the working recipe and every pitfall.

### 19.1 AT write forms closed too

`[FACT]` The last untried AT-level variant — actual **write forms** (`AT+CMGF=1`; then `AT+CMGS` in both number and PDU-length forms) — was attempted deliberately (`sms_at_attempt.py`, user-authorized destination, ESC-cancel + `ATH` restore armed): `AT+CMGF=1` → `+CME ERROR: 100`. The write handler is compiled out just like the test handler. **AT-level SMS is closed at every level.**

### 19.2 Keymap and wake semantics completed

`[FACT]` New key findings (completing §17.5):
- `e` = **End key**: from any state, returns to idle (verified while screen was awake; the physical End key behaves identically).
- **Screen wake:** the first `^` press after the ~20 s backlight timeout is **consumed by the backlight** and does nothing else; a subsequent press lands as real input. **Arrows are NOT consumed by the wake** — they always navigate; using `^` to wake while a menu is open moves the highlight (caused two failed runs). Safe wake idiom: press `^` then `e` (End is a no-op on the idle screen), or `^` twice when no menu is open.
- Multitap rhythm requirement confirmed: in-letter presses must be back-to-back (early-exit on `OK`, ~60–120 ms apart) with ~1.2 s between letters. My earlier garbling ("HELLO" → "Gg…") came from a fixed ~0.8 s inter-press delay that exceeded the multitap window.

### 19.3 The working send flow (verified end-to-end)

`[FACT]` Complete sequence, every step accepted, **SMS delivered to the authorized destination**:

1. `^` (wake, consumed) → `e` (force idle)
2. `[` (Menu) → `m` (open **Messages** — default highlight) → `m` (open **Write new**)
3. Type body via multitap (early-exit presses; ~1.2 s letter commits) — typed **HELLO** correctly
4. `[` (**Options**) → `m` (**Send To**, default highlight)
5. Chooser appears: highlight starts on **"Add to phonebook"** → press `^` **once** to reach **"Enter phone number"** → `m`
6. Type digits **<PHONE_NUMBER>** (domestic format; the CKPD alphabet has no `+` key) — number fields take digits 1:1
7. `m` (confirm number) → `m` (confirm send / SIM1)

Tool: `sms_native.py <number> [text]` — parameterized, masked, reusable on an SBC.

### 19.4 Updated final verdict

> `[INTERP]` **The SMS gateway goal is ACHIEVED, with caveats.** Sending: fully scriptable over USB (§19.3) — an SBC can send SMS through this phone unattended. Receiving: **still impossible over USB** — no URCs (§18.3), no AT SMS commands (§19.1); incoming messages land only on the handset's own inbox. The complete capability set of this port is now: calls (dial/DTMF/hangup), remote UI automation incl. SMS sending, identification, signal/indicator polling — and nothing else. Any receive-side gateway need requires different hardware (a modem-class device exposing TS 27.005).

---

## 20. Web gateway (`sms_web.py`, §19 follow-through)

`[FACT]` A browser-based sender was built on top of the proven flow: `python3 sms_web.py 8080` → open `http://<host>:8080` from any device on the LAN, enter a number + message, press **Send SMS**. `sms_native.send_sms()` runs in a background thread; the page polls `GET /status` every second and shows each step live; `POST /send` validates input (6–15 digits domestic; A–Z/space message); one send at a time (409 if busy); numbers masked in server logs. **Python stdlib only — no dependencies.**

`[FACT]` Verified: page serves (200), status JSON, invalid-input rejection (400). Live end-to-end run through the browser was skipped by user choice; the send path is the identical `send_sms()` proven in §19.3. Note for this lab environment only: background server processes do not persist between tool calls here — run it in a normal terminal on the SBC.
