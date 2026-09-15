#!/usr/bin/env python3
"""The Throne -- a King-of-the-Hill hill service.

A single SHARED container that every team attacks. Whoever last planted a valid
claim for their team token is the "king"; CTFd's koth plugin polls /king every
tick and awards points to the holder. Holding requires continuously re-claiming,
because a claim is only accepted (and only counts) while its timestamp is fresh.

Claiming the throne (POST /throne) requires a signature:

    sig = HMAC_SHA1(HILL_KEY, f"{team}|{ts}")

HILL_KEY is server-side only. The intended way in (stage 1, the "puzzle") is the
access-control bug on /debug:

    /debug is meant to be reachable only from localhost, but it decides that by
    trusting the LEFT-MOST value of the X-Forwarded-For header. A client that
    simply sends `X-Forwarded-For: 127.0.0.1` is treated as internal and the
    endpoint hands back HILL_KEY.

With HILL_KEY, a team signs a fresh claim for THEIR token (read from the CTFd
"King of the Hill" page) and re-posts it every few seconds to keep the throne.
"""
import hashlib
import hmac
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

PORT = int(os.environ.get("PORT", "8080"))
HILL_KEY = os.environ.get("HILL_KEY", "")
SCORER_SECRET = os.environ.get("SCORER_SECRET", "")
SKEW = int(os.environ.get("SKEW", "45"))  # seconds a claim's ts may deviate

_state_lock = threading.Lock()
_king = {"token": "", "ts": 0.0}
_claims = 0
_started = time.time()


def _expected_sig(team: str, ts: str) -> str:
    return hmac.new(
        HILL_KEY.encode("utf-8"),
        "{}|{}".format(team, ts).encode("utf-8"),
        hashlib.sha1,
    ).hexdigest()


def _looks_internal(headers) -> bool:
    """The (intentionally broken) access check for /debug.

    Trusts the left-most X-Forwarded-For entry as the "real client" -- a textbook
    XFF spoofing bug. Any client can claim to be 127.0.0.1.
    """
    xff = headers.get("X-Forwarded-For", "")
    first = xff.split(",")[0].strip() if xff else ""
    return first in ("127.0.0.1", "::1", "localhost")


PAGE = """<!doctype html><meta charset="utf-8"><title>The Throne</title>
<h1>&#128081; The Throne &mdash; King of the Hill</h1>
<p>Node: <b>throne-01</b></p>
<p>Current king token: <code>{king}</code> &middot; claims served: {claims}</p>
<p>Seize the throne: <code>POST /throne</code> with a signed claim
(<code>{{"team": "&lt;your token&gt;", "ts": &lt;unix&gt;, "sig": "&lt;hmac&gt;"}}</code>).
Ops tooling lives on the internal-only <code>/debug</code>.</p>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "Throne/1.0"

    def _send(self, code, obj, ctype="application/json"):
        if ctype == "application/json":
            body = json.dumps(obj).encode("utf-8")
        else:
            body = obj.encode("utf-8", "replace")
        self.send_response(code)
        self.send_header(
            "Content-Type",
            ctype + ("; charset=utf-8" if ctype != "application/json" else ""),
        )
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        with _state_lock:
            king_preview = (_king["token"][:8] + "…") if _king["token"] else "(vacant)"
            claims = _claims
        if path in ("/", "/index.html"):
            self._send(200, PAGE.format(king=king_preview, claims=claims), "text/html")
            return
        if path == "/status":
            self._send(
                200,
                {
                    "service": "throne",
                    "uptime": int(time.time() - _started),
                    "king": king_preview,
                    "claims": claims,
                },
            )
            return
        if path == "/debug":
            # Internal-only ops endpoint -- but the check trusts XFF (the bug).
            if not _looks_internal(self.headers):
                self._send(403, {"error": "debug endpoint is internal only"})
                return
            self._send(
                200,
                {
                    "note": "ops diagnostics",
                    "hill_key": HILL_KEY,
                    "sig_scheme": "HMAC_SHA1(HILL_KEY, team + '|' + ts)",
                    "skew_seconds": SKEW,
                },
            )
            return
        if path == "/king":
            # Scorer-only: CTFd reads the current king to award points.
            if (
                self.headers.get("X-Scorer-Token", "") != SCORER_SECRET
                or not SCORER_SECRET
            ):
                self._send(403, {"error": "forbidden"})
                return
            with _state_lock:
                self._send(200, {"token": _king["token"], "ts": _king["ts"]})
            return
        self._send(404, {"error": "not found"})

    def do_POST(self):
        global _claims
        path = urlparse(self.path).path
        if path != "/throne":
            self._send(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw.decode("utf-8", "replace")) if raw else {}
        except ValueError:
            self._send(400, {"error": "invalid json"})
            return
        team = str(body.get("team", "")).strip()
        ts = str(body.get("ts", "")).strip()
        sig = str(body.get("sig", "")).strip()
        if not team or not ts or not sig:
            self._send(400, {"error": "team, ts and sig are required"})
            return
        # Freshness: the claim's ts must be close to now (stops stale replays and
        # forces continuous re-claiming to keep the throne).
        try:
            if abs(time.time() - float(ts)) > SKEW:
                self._send(400, {"error": "stale claim (ts outside skew window)"})
                return
        except ValueError:
            self._send(400, {"error": "ts must be a unix timestamp"})
            return
        if not hmac.compare_digest(_expected_sig(team, ts), sig):
            self._send(401, {"error": "bad signature"})
            return
        with _state_lock:
            _king["token"] = team
            _king["ts"] = time.time()
            _claims += 1
            king_preview = team[:8] + "…"
        self._send(200, {"ok": True, "king": king_preview})

    def log_message(self, fmt, *args):  # keep container logs quiet
        pass


if __name__ == "__main__":
    if not HILL_KEY or not SCORER_SECRET:
        raise SystemExit("HILL_KEY and SCORER_SECRET must be set")
    httpd = ThreadingHTTPServer(
        ("0.0.0.0", PORT), Handler
    )  # nosec B104 - shared hill, must listen on all interfaces
    print("[throne] listening on 0.0.0.0:%d" % PORT, flush=True)
    httpd.serve_forever()
