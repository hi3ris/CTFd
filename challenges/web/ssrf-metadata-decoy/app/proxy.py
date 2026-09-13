"""
Public-facing image-fetch proxy (the SSRF surface).

The proxy fetches a user-supplied URL and streams back the bytes. It has a
naive "internal host" blocklist that only rejects the exact literal
"127.0.0.1" / "localhost" / "::1". That is the intended, realistic weakness:
loopback has a whole /8 (127.0.0.0/8) and dozens of alternate encodings, so
any of 127.0.0.2, 127.1, 0x7f000002, 2130706434, ... reach the same stack.

Nothing about the flag lives in this file. The flag is only produced by the
internal admin service when its /admin/ping endpoint is actually hit
server-side (i.e. through this proxy). See app/internal.py.
"""
import ipaddress
import socket
from urllib.parse import urlparse

import requests
from flask import Flask, Response, request

app = Flask(__name__)

# Always connect straight to the target. trust_env=False means we ignore any
# HTTP(S)_PROXY / NO_PROXY in the environment, so the fetch behaves identically
# regardless of the host's proxy config -- essential for a deterministic SSRF.
_session = requests.Session()
_session.trust_env = False

# The public "robots.txt-like" file. It is the intended breadcrumb: it names
# the internal service-registry odd port. It also mentions the link-local
# metadata *mirror* (the decoy) as "legacy boto compatibility" so an attentive
# reader has a hint that it is not the real thing.
ROBOTS = """\
User-agent: *
Disallow: /fetch
Disallow: /static

# -- ops notes (do not ship to prod) ------------------------------------
# The app tier can reach an internal service-registry over the loopback mesh.
#   registry:  http://127.0.0.1:9137/           (app-tier only, never exposed)
# A link-local metadata *mirror* is kept alive only for legacy boto clients:
#   http://169.254.169.254/latest/meta-data/    (mirror; creds here are stale)
# Real service credentials/tokens are issued by the registry's admin endpoint.
# -----------------------------------------------------------------------
"""

# Only the exact obvious forms are blocked. This is deliberately weak.
_BLOCKED_SUBSTRINGS = ("127.0.0.1", "localhost", "::1")

MAX_BYTES = 512 * 1024
TIMEOUT = 4


def _host_is_blocked(host: str) -> bool:
    if not host:
        return True
    h = host.strip().lower().strip("[]")
    return any(bad in h for bad in _BLOCKED_SUBSTRINGS)


@app.route("/")
def index():
    return (
        "<h1>imgproxy</h1>"
        "<p>Fetch remote images through the company proxy so the CDN can "
        "cache and re-encode them.</p>"
        "<p>Usage: <code>/fetch?url=https://example.com/logo.png</code></p>"
        "<p>Internal / loopback targets are blocked for safety.</p>",
        200,
        {"Content-Type": "text/html"},
    )


@app.route("/robots.txt")
def robots():
    return Response(ROBOTS, mimetype="text/plain")


@app.route("/fetch")
def fetch():
    url = request.args.get("url", "")
    if not url:
        return Response("missing ?url=", status=400, mimetype="text/plain")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return Response("only http/https are allowed", status=400, mimetype="text/plain")

    if _host_is_blocked(parsed.hostname or ""):
        return Response(
            "blocked: internal/loopback host not allowed",
            status=403,
            mimetype="text/plain",
        )

    try:
        # Stream so we can cap the size; relay the upstream body verbatim.
        with _session.get(
            url,
            stream=True,
            timeout=TIMEOUT,
            allow_redirects=False,
            headers={"User-Agent": "imgproxy/1.0"},
        ) as upstream:
            body = upstream.raw.read(MAX_BYTES + 1, decode_content=True) or b""
            if len(body) > MAX_BYTES:
                body = body[:MAX_BYTES]
            ctype = upstream.headers.get("Content-Type", "application/octet-stream")
            return Response(body, status=upstream.status_code, mimetype=ctype)
    except requests.exceptions.RequestException as exc:
        return Response(f"upstream fetch failed: {exc}", status=502, mimetype="text/plain")


# Small convenience for local sanity checks only.
def _resolves(host: str) -> str:
    try:
        return socket.gethostbyname(host)
    except OSError:
        return "?"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
