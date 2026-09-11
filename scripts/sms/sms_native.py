"""Native SMS sender for Lava E10 (MT6261) over USB COM port - PROVEN WORKING.

Sends a real SMS by driving the phone's native Messages app via AT+CKPD.
No AT-SMS support exists on this firmware (see ../../docs/overview/info.md §17-§19); this is
the only SMS path, demonstrated successfully on 2026-09-11 (§19).

Keymap (established empirically, ../../docs/overview/info.md §17.5/§19):
  [ = left softkey (Menu from idle / Options in editor)
  m = center OK    ] = right softkey    e = End key (to idle)
  ^ v < > = arrows (NOT consumed by screen wake - never use for waking)
  0-9 = multitap letters in ABC mode / literal digits in number fields

Timing rules (hard-won):
- Screen blanks after ~20 s idle: FIRST press must be ^ (wake) and is
  consumed by the backlight; a second press is needed for real input.
- Multitap: presses within a letter must be back-to-back (early-exit on
  'OK', ~60-120 ms apart); ~1.2 s gap commits the letter.
- Number fields take digits 1:1, no timing sensitivity.
- After Options -> "Send To", a chooser appears with "Add to phonebook"
  highlighted; press UP once to reach "Enter phone number", then OK.

Usage:
  python3 sms_native.py <number> [text]
  python3 sms_native.py <PHONE_NUMBER> "HELLO"
"""
import re
import sys
import time

import serial

PORT = "/dev/ttyACM0"
BAUD = 115200
MASK = re.compile(rb"(?<!\d)(\d{4})\d{6,}(\d{2})(?!\d)")

MULTITAP = {
    "A": ("2", 1), "B": ("2", 2), "C": ("2", 3),
    "D": ("3", 1), "E": ("3", 2), "F": ("3", 3),
    "G": ("4", 1), "H": ("4", 2), "I": ("4", 3),
    "J": ("5", 1), "K": ("5", 2), "L": ("5", 3),
    "M": ("6", 1), "N": ("6", 2), "O": ("6", 3),
    "P": ("7", 1), "Q": ("7", 2), "R": ("7", 3), "S": ("7", 4),
    "T": ("8", 1), "U": ("8", 2), "V": ("8", 3),
    "W": ("9", 1), "X": ("9", 2), "Y": ("9", 3), "Z": ("9", 4),
    " ": ("0", 1),
}


def press(ser, key, wait=1.0, progress=None):
    ser.reset_input_buffer()
    payload = f'AT+CKPD="{key}"\r'.encode()
    ser.write(payload)
    buf = bytearray()
    cap = time.monotonic() + wait
    while time.monotonic() < cap:
        n = ser.in_waiting
        if n:
            buf.extend(ser.read(n))
            if b"OK" in bytes(buf):
                break
        time.sleep(0.01)
    out = MASK.sub(rb"\1######\2", bytes(buf)).replace(
        b"\r", b"").decode("latin-1").strip()
    if progress:
        progress(f'key "{key}"')
    else:
        print(f'  "{key}" -> {out!r}', flush=True)
    return out


def send_sms(number, text="HELLO", progress=None, resume_editor=False):
    """Send an SMS through the native Messages app.

    ``resume_editor`` is used after a successful send.  The phone leaves
    ``Write new`` selected, so the left softkey opens the editor directly;
    walking back through Menu > Messages would unnecessarily reset the flow.

    Every key goes through an inactivity guard.  If the phone has been idle
    for 20 seconds or more, ``^`` wakes the screen (and is consumed by the
    backlight) before the pending key is sent.  This lets the sequence resume
    at the exact next key rather than starting over.

    progress: optional callable(str) receiving human-readable step updates
    (used by the web gateway); defaults to printing to stdout.
    """
    screen_idle_seconds = 20.0
    # Keep the last keypad activity across web requests.  This matters when a
    # later message is sent after the handset has gone dark between requests.
    last_key_at = getattr(send_sms, "_last_key_at", None)

    def step(msg):
        if progress:
            progress(msg)
        else:
            print(f"  # {msg}", flush=True)

    ser = serial.Serial(PORT, BAUD, timeout=0.1)

    def key(k, wait=1.0, force=False):
        nonlocal last_key_at
        now = time.monotonic()
        if (not force and last_key_at is not None
                and now - last_key_at >= screen_idle_seconds):
            idle_for = int(now - last_key_at)
            step(f"screen idle for {idle_for}s; waking and continuing")
            press(ser, "^", wait=1.0, progress=progress)
            last_key_at = time.monotonic()
            send_sms._last_key_at = last_key_at
            time.sleep(0.8)                 # wake press is consumed
        press(ser, k, wait=wait, progress=progress)
        last_key_at = time.monotonic()
        send_sms._last_key_at = last_key_at

    try:
        if resume_editor:
            # After a send, Write new is already highlighted.  [ is the
            # left-softkey action that opens that highlighted editor.
            step("resuming at Write new")
            key("["); time.sleep(1.5)
        else:
            # First send (or an unknown phone state): wake and force idle,
            # then use the proven Menu > Messages > Write new path.
            step("waking screen, forcing idle")
            key("^", force=True); time.sleep(0.8)  # consumed by backlight
            key("e"); time.sleep(1.5)              # End -> idle
            step("opening Menu > Messages > Write new")
            key("["); time.sleep(1.5)              # left softkey = Menu
            key("m"); time.sleep(1.5)              # Messages
            key("m"); time.sleep(1.8)              # Write new

        # Type text via multitap.
        step(f"typing {text!r}")
        for ch in text.upper():
            if ch not in MULTITAP:
                continue                         # skip unsupported chars
            tkey, count = MULTITAP[ch]
            for _ in range(count):
                key(tkey, wait=0.45)             # back-to-back, early-exit
            time.sleep(1.2)                      # commit letter

        # Options -> Send To.
        step("opening Options > Send To")
        key("["); time.sleep(1.5)                # Options
        key("m"); time.sleep(1.8)                # Send To

        # Chooser: UP once to Enter phone number, then OK.
        step("choosing Enter phone number")
        key("^"); time.sleep(1.0)
        key("m"); time.sleep(1.8)

        # Digits (1:1, no timing risk).
        step("entering recipient number")
        for d in number:
            if d in "0123456789":
                key(d, wait=0.5)
                time.sleep(0.3)

        # Confirm: OK (accept number), OK (send / SIM1).
        step("confirming send")
        key("m"); time.sleep(2.0)
        key("m"); time.sleep(3.0)
        step("DONE - SMS should be transmitting")
    finally:
        send_sms._last_key_at = last_key_at
        ser.close()


def main():
    if len(sys.argv) < 2:
        sys.exit('usage: sms_native.py <number> [text]  '
                 'e.g. sms_native.py <PHONE_NUMBER> "HELLO"')
    number = sys.argv[1].strip()
    if not re.fullmatch(r"[0-9]{6,15}", number):
        sys.exit("number must be 6-15 digits (domestic format, no +)")
    text = sys.argv[2] if len(sys.argv) > 2 else "HELLO"
    text = "".join(c for c in text.upper() if c in MULTITAP)
    if not text:
        sys.exit("text has no typeable characters (A-Z, space)")
    print(f"sending to {number[:3]}{'#' * (len(number) - 5)}{number[-2:]}: "
          f"{text!r}", flush=True)
    send_sms(number, text)


if __name__ == "__main__":
    main()
