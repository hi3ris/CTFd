#!/usr/bin/env python3
"""Kékéli Cloud -- "breach chain" scenario (SSRF -> IMDS -> stolen creds -> flag).

One per-team container hosts the whole kill chain:

  * PUBLIC app (0.0.0.0:PORT): a thumbnail/preview service with an SSRF in
    /fetch, plus a credential-gated admin endpoint /api/admin/secrets.
  * INTERNAL instance-metadata service (127.0.0.1:META_PORT): an IMDSv1-style
    endpoint that hands out the app role's temporary credentials. It is NOT
    directly reachable by the player -- only the app host can talk to it, i.e.
    only through the SSRF.

Intended chain:

  1. SSRF: /fetch?url= blocks the obvious internal literals (127.0.0.1,
     localhost, ::1) but not `0.0.0.0`, so
       /fetch?url=http://0.0.0.0:META_PORT/latest/meta-data/iam/security-credentials/
     reaches the internal metadata service.
  2. IMDS: read the app role's credentials; the `Token` is the temporary
     session token (there is one decoy role whose token is expired/rejected).
  3. Stolen creds: replay that Token to the PUBLIC endpoint
       GET /api/admin/secrets   with header  X-App-Token: <Token>
     which returns the flag.

The flag is only returned by /api/admin/secrets, and the Token that unlocks it
is only obtainable via the SSRF -> IMDS path, so the effect (using a
correctly-stolen credential) IS the win condition.
"""
import hashlib
import hmac
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import urllib.request
import urllib.error

import flag as flagmod

PORT = int(os.environ.get("PORT", "8080"))
META_HOST = "127.0.0.1"
META_PORT = int(os.environ.get("META_PORT", "8169"))
APP_SECRET = os.environ.get("APP_SECRET", "kekeli-internal-secret")
ROLE = "kekeli-app-role"
DECOY_ROLE = "legacy-backup-role"
FLAG = flagmod.get_flag()

# The temporary session token the app role would receive from the metadata
# service. Unguessable without reading it out of IMDS via the SSRF.
APP_TOKEN = hmac.new(
    APP_SECRET.encode("utf-8"), ROLE.encode("utf-8"), hashlib.sha256
).hexdigest()[:32]

# SSRF blocklist: naive literal blocking (the bug is what it MISSES).
_BLOCKED_HOSTS = {"127.0.0.1", "localhost", "::1", "[::1]"}


def _html(body):
    return body.encode("utf-8", "replace")


# --------------------------------------------------------------------------
# Internal instance-metadata service (127.0.0.1:META_PORT)
# --------------------------------------------------------------------------
class MetaHandler(BaseHTTPRequestHandler):
    server_version = "EC2ws/IMDS"

    def _send(self, code, body, ctype="text/plain"):
        data = body if isinstance(body, bytes) else body.encode("utf-8", "replace")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        base = "/latest/meta-data/iam/security-credentials"
        if path in ("/", "/latest/meta-data/"):
            self._send(200, "iam/\n")
            return
        if path == base or path == base + "/":
            # Two roles are attached; only one is the live app role.
            self._send(200, "{}\n{}\n".format(ROLE, DECOY_ROLE))
            return
        if path == base + "/" + ROLE:
            self._send(
                200,
                json.dumps(
                    {
                        "Code": "Success",
                        "Type": "AWS-HMAC",
                        "AccessKeyId": "AKIA" + APP_TOKEN[:16].upper(),
                        "Token": APP_TOKEN,
                        "Expiration": "2099-01-01T00:00:00Z",
                    }
                ),
                "application/json",
            )
            return
        if path == base + "/" + DECOY_ROLE:
            # Decoy: a plausible but expired/rejected token.
            self._send(
                200,
                json.dumps(
                    {
                        "Code": "Success",
                        "Type": "AWS-HMAC",
                        "AccessKeyId": "AKIALEGACYBACKUP0000",
                        "Token": "expired-" + "0" * 24,
                        "Expiration": "2019-01-01T00:00:00Z",
                    }
                ),
                "application/json",
            )
            return
        self._send(404, "not found\n")

    def log_message(self, fmt, *args):
        pass


# --------------------------------------------------------------------------
# Public app (0.0.0.0:PORT)
# --------------------------------------------------------------------------
INDEX = """<!doctype html><meta charset="utf-8"><title>Kékéli Cloud</title>
<h1>Kékéli Cloud &mdash; media preview</h1>
<p>Node: <b>app-01</b> &middot; region: <code>tg-lome-1</code></p>
<p>Preview any image/URL server-side:</p>
<form action="/fetch" method="get">
  <input name="url" value="http://example.com/" size="48"><button>preview</button>
</form>
<p style="color:#888">The renderer runs on the app instance and can reach the
platform's internal services.</p>
"""


class AppHandler(BaseHTTPRequestHandler):
    server_version = "kekeli-app/1.0"

    def _send(self, code, body, ctype="text/html"):
        data = body if isinstance(body, bytes) else body.encode("utf-8", "replace")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self._send(200, INDEX)
            return
        if parsed.path == "/fetch":
            url = parse_qs(parsed.query).get("url", [""])[0]
            self._fetch(url)
            return
        if parsed.path == "/api/admin/secrets":
            # Credential-gated: only a valid stolen app-role Token unlocks it.
            token = self.headers.get("X-App-Token", "")
            if hmac.compare_digest(token, APP_TOKEN):
                self._send(200, json.dumps({"flag": FLAG}), "application/json")
            else:
                self._send(
                    401,
                    json.dumps({"error": "invalid or missing X-App-Token"}),
                    "application/json",
                )
            return
        self._send(404, "<h1>404</h1>")

    def _fetch(self, url):
        try:
            p = urlparse(url)
        except ValueError:
            self._send(400, "<pre>bad url</pre>")
            return
        if p.scheme not in ("http", "https"):
            self._send(400, "<pre>only http(s) urls are supported</pre>")
            return
        host = (p.hostname or "").lower()
        # --- VULNERABILITY: naive literal blocklist (misses 0.0.0.0, decimal, …)
        if host in _BLOCKED_HOSTS:
            self._send(403, "<pre>blocked: internal host</pre>")
            return
        try:
            with urllib.request.urlopen(url, timeout=6) as r:  # nosec B310
                body = r.read(65536).decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            body = "HTTP {}\n{}".format(e.code, e.read(4096).decode("utf-8", "replace"))
        except Exception as e:  # noqa: BLE001
            self._send(502, "<pre>fetch failed: {}</pre>".format(e))
            return
        import html as _h

        self._send(
            200,
            "<h2>preview of {}</h2><pre>{}</pre>".format(
                _h.escape(url), _h.escape(body)
            ),
        )

    def log_message(self, fmt, *args):
        pass


def _serve_meta():
    ThreadingHTTPServer((META_HOST, META_PORT), MetaHandler).serve_forever()


if __name__ == "__main__":
    threading.Thread(target=_serve_meta, daemon=True).start()
    print("[app] internal IMDS on {}:{}".format(META_HOST, META_PORT), flush=True)
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), AppHandler)  # nosec B104
    print("[app] public app on 0.0.0.0:{}".format(PORT), flush=True)
    httpd.serve_forever()
