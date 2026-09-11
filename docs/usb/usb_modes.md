# USB mode enumeration — Lava E10 (0e8d:0003 family) — capture template

Per handset USB mode (Settings → USB / "COM port" / "Mass storage" / PC-sync /
webcam etc.), run **only** the descriptor dumps below. **No AT commands** in
this phase — characterization only. Fill one block per mode, then summarize
VID:PID + interface classes + resulting device nodes in the comparison table.

## Commands (per mode)

```bash
lsusb | grep -i 0e8d
ls -l /dev/ttyACM* /dev/ttyUSB* /dev/sd* /dev/sr* 2>/dev/null
sudo usb-devices | sed -n '/Vendor=0e8d/,/^$/p'
lsusb -v -d 0e8d:XXXX 2>/dev/null | grep -E 'idProduct|bInterfaceClass|bInterfaceSubClass|bInterfaceProtocol|iInterface|bNumEndpoints'
sudo dmesg | tail -30
```

## Mode blocks (fill in)

### Mode: COM port (baseline, already characterized in ../overview/info.md §1–§3)

- VID:PID: 0e8d:0003 — one CDC ACM function (Data 0x0a + Comm 0x02/ACM/1), reversed interface order
- Nodes: /dev/ttyACM0 (root uucp 166:0)
- Configs: 3 (identical); full-speed; 500 mA; no serial string

### Mode: Mass storage (captured 2026-09-11 18:54, `usb_mode_mass_storage.md`)

- VID:PID: **0e8d:0002** (PID changed 0003 → 0002; `lsusb` name comes from a Doro entry in usb.ids — irrelevant)
- Interface: exactly one — class 08 (Mass Storage), subclass 06 (SCSI), protocol 50 (Bulk-Only), `usb-storage` bound
- Nodes: `/dev/sdc` (usb, Lava E10) — **0 B, no media: the microSD slot is empty; no card inserted**. Internal flash NOT exposed.
- Serial number string **PRESENT in this mode** (`<USB_SERIAL_REDACTED>`, masked per §12 policy) — absent in COM mode
- Configs: 3 (identical, like COM mode); same garbled strings; same bus/port 3-2
- No AT capability in this mode (no CDC interface at all)

## Comparison table

| Handset mode | VID:PID | Iface classes | tty nodes | block nodes | Notes |
|---|---|---|---|---|---|
| COM port | 0e8d:0003 | CDC Data 0a + CDC ACM 02/01 | ttyACM0 | — | baseline; no serial string |
| Mass storage | 0e8d:0002 | MSC 08/06/50 | — | sdc (0 B, no card) | serial string present; no AT |

## Menu inventory (observed 2026-09-11)

`[FACT]` The handset's USB menu offers **exactly two modes: "COM port" and "Mass storage"** (user-confirmed). No PC-suite/sync mode, no webcam, no diagnostic/VCOM mode, no charge-only entry.

`[INTERP]` With no dedicated sync mode, vendor PC-suite software on this model must speak either (a) AT-over-CDC-ACM in COM mode — the exact interface already probed exhaustively — or (b) drive the phone UI. This significantly lowers the expected payoff of the §15-D USB-sniffing phase for SMS discovery and deprioritizes it until a SIM is available and steps 3–4 are exhausted.

## What to look for

- A **mass storage** mode should show class 08 (MSC) with 2 bulk endpoints,
  and a `/dev/sd*` node — expected to expose the phone's microSD (if fitted),
  not firmware. Harmless to mount read-only.
- A **PC-sync / "sync tool"** mode is the interesting one: often a vendor
  protocol over a second ACM port or a vendor-specific class (0xFF). If it
  yields a second tty or a 0xFF interface, that is the §15-D sniffing target.
- **Diagnostic/VCOM-style** modes (MediaTek preloader/bootrom) usually appear
  only at boot or via special key combos and use 0e8d:0003/0e8d:2000/2001.
  Do NOT interact with flashing tools; characterization only.
- bcdDevice / iProduct changes between modes are useful fingerprints.
