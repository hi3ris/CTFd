#!/usr/bin/env python3
"""Boot2root KotH scorer -- the /king endpoint the CTFd koth plugin polls.

A boot2root hill is a SHARED SSH box with TWO king files:

    /root/king.txt          root-only (mode 0600 in /root, mode 0700)  -> "root"
    /home/player/king.txt    player-writable                           -> "user"

A team plants its opaque team token (read from the CTFd "King of the Hill"
page) into one of these. Writing the USER file needs only the `player` login;
writing the ROOT file needs a full privilege escalation. This scorer runs as
root and exposes whichever hold is currently active:

    GET /king   (header X-Scorer-Token: <SCORER_SECRET>)
      -> {"token": <content>, "ts": <mtime>, "level": "root"|"user"}

The freshest write wins (a hold must be continuously re-claimed, like every
KotH hill), and its level rides along: the CTFd plugin awards full points for
a root hold and HALF for a user-only hold. Root beats user on an exact tie, so
a team that reaches root is never undercut by its own leftover user file.
"""
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

PORT = int(os.environ.get("SCORER_PORT", "8082"))
SCORER_SECRET = os.environ.get("SCORER_SECRET", "")
ROOT_KING = os.environ.get("ROOT_KING", "/root/king.txt")
USER_KING = os.environ.get("USER_KING", "/home/player/king.txt")


def _read(path):
    """(token, mtime) for a king file, or ("", 0.0) if unreadable/empty."""
    try:
        with open(path) as fh:
            tok = fh.read().strip()
        if not tok:
            return "", 0.0
        return tok, os.path.getmtime(path)
    except OSError:
        return "", 0.0


def current_king():
    """The active hold: the more recently written of the two files. Root wins a
    tie so a stale user file never demotes a team that is holding root."""
    r_tok, r_ts = _read(ROOT_KING)
    u_tok, u_ts = _read(USER_KING)
    if r_tok and (not u_tok or r_ts >= u_ts):
        return {"token": r_tok, "ts": r_ts, "level": "root"}
    if u_tok:
        return {"token": u_tok, "ts": u_ts, "level": "user"}
    return {"token": "", "ts": 0.0, "level": "root"}


class Handler(BaseHTTPRequestHandler):
    server_version = "boot2root-scorer/1.0"

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
            self._send(200, current_king())
            return
        if path in ("/", "/status"):
            self._send(200, {"service": "boot2root", "uptime": int(time.time())})
            return
        self._send(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    if not SCORER_SECRET:
        raise SystemExit("SCORER_SECRET must be set")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()  # nosec B104
