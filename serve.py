#!/usr/bin/env python3
"""
serve.py — auto-refreshing live view of the dashboard.
======================================================
Logs in to Garmin ONCE (reusing the cached token), then re-fetches your data on
a timer in the background and serves the dashboard locally. Leave the browser
tab open and it updates itself — no manual re-runs.

    python serve.py
    # then open the URL it prints (http://localhost:8000)

Why not truly real-time? The unofficial Garmin login rate-limits hard, and
Garmin Connect itself only updates when your watch syncs (after a run, or every
few hours). So we refresh every REFRESH_MIN minutes — as live as the data gets.

Config (optional environment variables):
    PORT=8000            port to serve on
    REFRESH_MIN=15       minutes between background refreshes
"""

import os
import json
import time
import threading
import datetime as dt
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

import fetch_garmin as fg

PORT = int(os.getenv("PORT", "8000"))
REFRESH_MIN = float(os.getenv("REFRESH_MIN", "15"))
ROOT = os.path.dirname(os.path.abspath(__file__))

# Shared state, guarded by a lock (background thread writes, requests read).
_state = {"data": {}, "updatedAt": None, "status": "starting", "error": None}
_lock = threading.Lock()
_refresh = threading.Event()        # set by /api/refresh to trigger an immediate refetch


def refresh_loop():
    """Login once, then refetch on an interval. Backs off on rate limits."""
    try:
        g = fg.connect()
    except SystemExit as e:
        with _lock:
            _state["status"] = "login-failed"
            _state["error"] = str(e)
        print(f"Login failed: {e}")
        return

    backoff = 0
    while True:
        try:
            print(f"\n[{dt.datetime.now():%H:%M:%S}] refreshing from Garmin…")
            data = fg.fetch_all(g)
            fg.write_data_js(data)                      # keep garmin-data.js in sync too
            with _lock:
                _state.update(data=data, updatedAt=data.get("updatedAt"),
                              status="ok", error=None)
            runs = len(data.get("runs", []))
            print(f"[{dt.datetime.now():%H:%M:%S}] updated ({runs} runs). "
                  f"Next refresh in {REFRESH_MIN:g} min.")
            backoff = 0
        except Exception as e:                          # noqa: BLE001
            with _lock:
                _state["status"], _state["error"] = "error", str(e)
            backoff = min(backoff + 1, 4)
            wait = REFRESH_MIN * (2 ** backoff)
            print(f"Refresh error: {e} — backing off {wait:g} min")
            _refresh.wait(wait * 60); _refresh.clear()
            continue
        # Sleep until the interval elapses OR /api/refresh is requested.
        if _refresh.wait(REFRESH_MIN * 60):
            _refresh.clear()
            print("Manual refresh requested.")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def log_message(self, *a):                          # quieter console
        pass

    def do_POST(self):
        if self.path.split("?")[0].rstrip("/") == "/api/refresh":
            _refresh.set()
            self.send_response(202)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            return
        self.send_error(404)

    def do_GET(self):
        if self.path.split("?")[0] in ("/api/data", "/api/data/"):
            with _lock:
                body = json.dumps({
                    "status": _state["status"],
                    "updatedAt": _state["updatedAt"],
                    "error": _state["error"],
                    "data": _state["data"],
                }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return
        # default index -> dashboard
        if self.path in ("/", ""):
            self.path = "/dashboard.html"
        return super().do_GET()


def main():
    threading.Thread(target=refresh_loop, daemon=True).start()
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"\nLive dashboard serving at  {url}")
    print(f"Auto-refreshing every {REFRESH_MIN:g} min. Press Ctrl+C to stop.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
