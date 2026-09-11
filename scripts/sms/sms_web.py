"""Web SMS gateway for the Lava E10 - Python stdlib only (no dependencies).

Serves a single page where you enter a phone number and a message; sending
drives the phone's native Messages app over /dev/ttyACM0 via AT+CKPD
(the proven sms_native.send_sms flow - ../../docs/overview/info.md §19).

Run:   python3 sms_web.py [port]        (default 8000)
Open:  http://localhost:8000

- One send at a time (concurrent requests get 409 busy).
- Progress is polled from the browser every second (GET /status).
- Numbers are masked in server logs; the page never logs identifiers.
"""
import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

import sms_native

HOST = "0.0.0.0"
PORT_WEB = 8000
MASK = re.compile(r"(?<!\d)(\d{4})\d{6,}(\d{2})(?!\d)")

JOB = {"state": "idle", "steps": [], "number": None, "started": None,
       "finished": None, "ok": None, "resumed": False}
LOCK = threading.Lock()
# A successful send leaves the handset with Write new selected.  Keep this
# separately from JOB so the next request can enter the editor directly.
PHONE_READY_FOR_NEW = False


def log_masked(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def run_send(number, text, resume_editor):
    global PHONE_READY_FOR_NEW

    def progress(msg):
        JOB["steps"].append(msg)
        log_masked(f"{MASK.sub(r'\\1######\\2', number)}: {msg}")

    try:
        JOB["state"] = "running"
        JOB["steps"] = []
        sms_native.send_sms(number, text, progress=progress,
                             resume_editor=resume_editor)
        # The handset is now ready for the next message without reopening
        # Menu > Messages.  Only mark it ready after a completed send.
        with LOCK:
            PHONE_READY_FOR_NEW = True
            JOB["state"] = "done"
            JOB["ok"] = True
        progress("send sequence finished (verify receipt on handset network)")
    except Exception as e:            # noqa: BLE001 - report any failure to UI
        with LOCK:
            # After an interrupted sequence the handset position is unknown;
            # the next request must use the safe full navigation path.
            PHONE_READY_FOR_NEW = False
            JOB["state"] = "error"
            JOB["ok"] = False
            JOB["steps"].append(f"ERROR: {e}")
        log_masked(f"ERROR: {e}")
    finally:
        JOB["finished"] = time.time()


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lava E10 SMS Gateway</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { font-family: system-ui, sans-serif; background:#0f1420; color:#e8ecf4;
         display:flex; justify-content:center; padding:24px; margin:0; }
  .card { background:#171f30; border:1px solid #2a3650; border-radius:14px;
          padding:28px; width:100%; max-width:460px; }
  h1 { font-size:1.25rem; margin:0 0 4px; }
  .sub { color:#8fa0bd; font-size:.85rem; margin-bottom:22px; }
  label { display:block; font-size:.8rem; color:#8fa0bd; margin:14px 0 6px; }
  input, textarea { width:100%; background:#0f1420; color:#e8ecf4;
          border:1px solid #2a3650; border-radius:8px; padding:11px 12px;
          font-size:1rem; }
  textarea { resize:vertical; min-height:90px; }
  .hint { font-size:.72rem; color:#5f7093; margin-top:4px; }
  button { width:100%; margin-top:20px; padding:13px; border:0;
          border-radius:8px; background:#2f6fed; color:#fff; font-size:1rem;
          font-weight:600; cursor:pointer; }
  button:disabled { background:#243250; color:#7787a5; cursor:not-allowed; }
  #status { margin-top:18px; font-size:.85rem; }
  .pill { display:inline-block; padding:3px 10px; border-radius:999px;
          font-size:.75rem; font-weight:600; }
  .idle   { background:#243250; color:#8fa0bd; }
  .running{ background:#3d3413; color:#ffd75e; }
  .done   { background:#12351f; color:#57d98a; }
  .error  { background:#3b1519; color:#ff7b81; }
  ul { margin:10px 0 0; padding-left:18px; color:#aab8d0;
       max-height:220px; overflow-y:auto; }
  li { margin:3px 0; font-family:ui-monospace,monospace; font-size:.78rem; }
</style>
</head>
<body>
<div class="card">
  <h1>Lava E10 — SMS Gateway</h1>
  <div class="sub">Sends a real SMS by driving the phone's native Messages
  app over USB (AT+CKPD). Takes ~45&ndash;60&nbsp;s. Keep the screen awake
  &amp; hands off the keypad.</div>

  <form id="f">
    <label for="number">Phone number</label>
    <input id="number" name="number" inputmode="numeric" autocomplete="off"
           placeholder="98XXXXXXXX" required
           pattern="[0-9]{6,15}">
    <div class="hint">Domestic digits only (no +). 6&ndash;15 digits.</div>

    <label for="text">Message</label>
    <textarea id="text" name="text" maxlength="120" required
      placeholder="HELLO">HELLO</textarea>
    <div class="hint">Uppercase A&ndash;Z and spaces only (multitap input).
      Max 120 chars.</div>

    <button id="btn" type="submit">Send SMS</button>
  </form>

  <div id="status">
    <span class="pill idle" id="pill">idle</span>
    <span id="stepcount"></span>
    <ul id="log"></ul>
  </div>
</div>

<script>
const pill = document.getElementById('pill');
const log = document.getElementById('log');
const btn = document.getElementById('btn');
const stepcount = document.getElementById('stepcount');
let poller = null;

function setPill(state) {
  pill.className = 'pill ' + state;
  pill.textContent = state;
}

async function poll() {
  try {
    const r = await fetch('/status');
    const j = await r.json();
    setPill(j.state);
    stepcount.textContent = j.steps.length ? j.steps.length + ' steps' : '';
    log.innerHTML = j.steps.map(s => '<li>' + s + '</li>').join('');
    log.scrollTop = log.scrollHeight;
    const busy = (j.state === 'running');
    btn.disabled = busy;
    btn.textContent = busy ? 'Sending… (do not touch the phone)' : 'Send SMS';
    if (!busy && poller) { clearInterval(poller); poller = null; }
  } catch (e) { /* server restarted etc. */ }
}

document.getElementById('f').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const number = document.getElementById('number').value.trim();
  const text = document.getElementById('text').value;
  const r = await fetch('/send', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: new URLSearchParams({number, text})
  });
  const j = await r.json();
  if (!r.ok) { alert(j.error || 'request failed'); return; }
  setPill('running');
  if (!poller) poller = setInterval(poll, 1000);
  poll();
});

poll();
poller = setInterval(poll, 1000);   // keep UI synced even if page (re)opened mid-send
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):     # silence default request logging
        pass

    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index"):
            self._send(200, PAGE)
        elif self.path == "/status":
            with LOCK:
                snap = {k: (list(v) if isinstance(v, list) else v)
                        for k, v in JOB.items()}
            self._send(200, json.dumps(snap), "application/json")
        else:
            self._send(404, "not found", "text/plain")

    def do_POST(self):
        if self.path != "/send":
            self._send(404, "not found", "text/plain")
            return
        length = int(self.headers.get("Content-Length", 0))
        fields = parse_qs(self.rfile.read(length).decode())
        number = (fields.get("number", [""])[0] or "").strip()
        text = (fields.get("text", [""])[0] or "").strip()

        if not re.fullmatch(r"[0-9]{6,15}", number):
            self._send(400, json.dumps(
                {"error": "number must be 6-15 digits, domestic format"}),
                "application/json")
            return
        clean = "".join(c for c in text.upper() if c in sms_native.MULTITAP)
        if not clean:
            self._send(400, json.dumps(
                {"error": "message must contain A-Z and/or spaces"}),
                "application/json")
            return

        with LOCK:
            if JOB["state"] == "running":
                self._send(409, json.dumps(
                    {"error": "a send is already in progress"}),
                    "application/json")
                return
            resume_editor = PHONE_READY_FOR_NEW
            JOB["state"] = "running"
            JOB["steps"] = []
            JOB["number"] = MASK.sub(r"\1######\2", number)
            JOB["started"] = time.time()
            JOB["finished"] = None
            JOB["ok"] = None
            JOB["resumed"] = resume_editor
            t = threading.Thread(target=run_send,
                                 args=(number, clean, resume_editor),
                                 daemon=True)
            t.start()
        log_masked(f"accepted send to {MASK.sub(r'\\1######\\2', number)} "
                   f"({len(clean)} chars; "
                   f"{'resuming at Write new' if resume_editor else 'full start'})")
        self._send(200, json.dumps({"started": True, "text": clean,
                                    "resumed": resume_editor}),
                   "application/json")


def main():
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT_WEB
    srv = ThreadingHTTPServer((HOST, port), Handler)
    print(f"SMS gateway listening on http://0.0.0.0:{port} "
          f"(Ctrl+C to stop)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
