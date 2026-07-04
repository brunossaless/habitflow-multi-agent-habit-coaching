#!/usr/bin/env python3
"""HabitFlow Team — web server + sprint API.

Usage:
    python3 server.py
    # open http://localhost:8080
"""

import json
import os
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).parent
WEB_DIR = ROOT / "web"
sys.path.insert(0, str(ROOT))

from runtime.orchestrator import HabitOrchestrator  # noqa: E402

PORT = int(os.environ.get("PORT", "8080"))
orchestrator = HabitOrchestrator()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _json(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/health":
            self._json(200, {"status": "ok", "project": "habitflow-team"})
            return
        if self.path == "/api/board":
            from mcp_server.store import board_get
            self._json(200, board_get())
            return
        super().do_GET()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            body = {}

        if self.path == "/api/sprint/run":
            result = orchestrator.run_sprint(
                user_input=body.get("input", "Check-in diário"),
                user_id=body.get("user_id", "demo-user"),
                mode=body.get("mode", "auto"),
            )
            self._json(200, result)
            return

        if self.path == "/api/demo/seed":
            from runtime.executors import seed_demo_logs
            uid = body.get("user_id", "demo-user")
            seed_demo_logs(uid)
            self._json(200, {"seeded": True, "user_id": uid})
            return

        self.send_error(404)


def main():
    port = PORT
    server = None
    for candidate in range(PORT, PORT + 10):
        try:
            server = ThreadingHTTPServer(("", candidate), Handler)
            port = candidate
            break
        except OSError as e:
            if e.errno != 48:
                raise
    if server is None:
        raise SystemExit(f"Nenhuma porta livre entre {PORT} e {PORT + 9}")
    print(f"HabitFlow Team → http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
