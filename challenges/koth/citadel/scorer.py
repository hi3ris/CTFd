#!/usr/bin/env python3
"""Citadel scorer -- the /king endpoint the CTFd koth plugin polls.

The Citadel is a SHARED SSH box. The "king" is whoever last wrote their team
token into the root-only file /koth/king (writable only as root). This tiny HTTP
server runs as root inside the container and exposes that file to CTFd:

    GET /king   (header X-Scorer-Token: <SCORER_SECRET>)
      -> {"token": <content of /koth/king>, "ts": <its mtime>}

The koth plugin maps the token back to a team and awards points while the claim
is fresh, so holding the Citadel means staying root and re-writing the file
faster than the other teams overwrite it -- classic root-wars King of the Hill.
"""
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

PORT = int(os.environ.get("SCORER_PORT", "8081"))
SCORER_SECRET = os.environ.get("SCORER_SECRET", "")
KING_FILE = os.environ.get("KING_FILE", "/koth/king")


class Handler(BaseHTTPRequestHandler):
    server_version = "citadel-scorer/1.0"

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/king":
            if (
                self.headers.get("X-Scorer-Token", "") != SCORER_SECRET
                or not SCORER_SECRET
            ):
                self._send(403, {"error": "forbidden"})
                return
            try:
                with open(KING_FILE) as fh:
                    tok = fh.read().strip()
                ts = os.path.getmtime(KING_FILE)
            except OSError:
                tok, ts = "", 0
            self._send(200, {"token": tok, "ts": ts})
            return
        if path in ("/", "/status"):
            self._send(200, {"service": "citadel", "uptime": int(time.time())})
            return
        self._send(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    if not SCORER_SECRET:
        raise SystemExit("SCORER_SECRET must be set")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()  # nosec B104
