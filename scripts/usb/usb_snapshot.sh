#!/usr/bin/env bash
# One-shot USB mode snapshot: run right after switching the handset's USB mode.
# Usage: usb_snapshot.sh <mode-name>   e.g. ./usb_snapshot.sh mass_storage
# Characterization only — sends nothing to the phone.
set -u
MODE="${1:-unnamed}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="$ROOT/captured-output/usb/usb_mode_${MODE}.md"
DEVNODES=$(ls -l /dev/ttyACM* /dev/ttyUSB* /dev/sd* /dev/sr* 2>/dev/null || true)
VIDPID=$(lsusb | grep -i 0e8d | head -1)
PID=$(echo "$VIDPID" | grep -oE '0e8d:[0-9a-f]{4}' | cut -d: -f2)

{
  echo "# USB mode snapshot: ${MODE} — $(date '+%Y-%m-%d %H:%M:%S')"
  echo
  echo "## lsusb"
  echo '```text'
  echo "${VIDPID:-NOT FOUND}"
  echo '```'
  echo
  echo "## device nodes"
  echo '```text'
  echo "${DEVNODES:-none}"
  echo '```'
  echo
  echo "## usb-devices"
  echo '```text'
  usb-devices 2>/dev/null | sed -n '/Vendor=0e8d/,/^$/p'
  echo '```'
  echo
  echo "## lsusb -v (interfaces, filtered; PID=${PID:-unknown})"
  echo '```text'
  [ -n "$PID" ] && lsusb -v -d "0e8d:$PID" 2>/dev/null | \
    grep -E 'idProduct|bInterfaceClass|bInterfaceSubClass|bInterfaceProtocol|iInterface|bNumEndpoints|bcdDevice'
  echo '```'
  echo
  echo "## dmesg tail"
  echo '```text'
  dmesg 2>/dev/null | tail -25 || sudo dmesg | tail -25
  echo '```'
} > "$OUT" 2>&1

echo "wrote $OUT"
cat "$OUT"
