"""Webhook Relay — a callback validator that can be tricked into SSRF.

Design (served challenge, per-team flag):

  * ``/webhook/deliver?url=`` validates the callback URL then fetches it
    server-side. The validation is a substring check: the URL must *contain*
    ``hooks.partner.example`` (the allow-listed partner host). That is trivially
    bypassed — e.g. ``http://169.254.169.254/...#hooks.partner.example`` contains
    the string but resolves to the internal metadata host.
  * The internal metadata host mints a deploy token and, at
    ``/latest/meta-data/flag``, returns the instance secret. It is reachable only
    from the server.

Intended path: pass a URL that satisfies the substring check but points at the
internal metadata flag endpoint.

The flag at ``/flag.txt`` is exposed only through the internal metadata host the
relayed request reaches server-side.
"""
import os
from urllib.parse import urlparse

from flask import Flask, jsonify, request

app = Flask(__name__)

ALLOWED_SUBSTRING = "hooks.partner.example"


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{flag-unavailable-in-dev}"


def _server_fetch(url):
    # Server-side fetch. The internal metadata host is only reachable here.
    host = urlparse(url).hostname
    if host == "169.254.169.254":
        path = urlparse(url).path
        if path == "/latest/meta-data/flag":
            return _flag()
        if path == "/latest/meta-data/role":
            return "backup-restore"
        return "<metadata>"
    return "<partner webhook ack>"


@app.route("/")
def index():
    return jsonify(
        {
            "service": "webhook-relay",
            "deliver": "/webhook/deliver?url=<callback>",
            "policy": f"callback URL must reference {ALLOWED_SUBSTRING}",
        }
    )


@app.route("/webhook/deliver")
def deliver():
    url = request.args.get("url", "")
    # BUG: a substring check, not a host check — bypassable via fragment/userinfo.
    if ALLOWED_SUBSTRING not in url:
        return jsonify({"error": "callback host not allowed"}), 403
    return jsonify({"delivered": True, "response": _server_fetch(url)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
