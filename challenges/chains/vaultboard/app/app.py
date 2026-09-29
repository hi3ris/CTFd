"""Vaultboard — a chain: SSRF → internal scoped token → mis-ACL'd object.

Design (served challenge, per-team flag):

  Stage 1 (SSRF): ``/fetch?url=`` fetches server-side. The internal STS at
    ``http://127.0.0.1/internal/sts`` (reachable only server-side) mints a token
    scoped to ``read:backups``.
  Stage 2 (mis-ACL): ``/object?key=&token=`` serves objects. The ``read:backups``
    scope is wrongly allowed to read ``private/flag`` (the object's ACL lists the
    backups scope by mistake).

Each stage unlocks the next: the SSRF yields the token, the token reads the
mis-ACL'd object. The flag at ``/flag.txt`` is served by no route.
"""
import os
import secrets

from flask import Flask, jsonify, request

app = Flask(__name__)

_TOKEN = "sts-" + secrets.token_hex(8)
# object key -> scopes allowed to read it. private/flag wrongly lists read:backups.
ACL = {"public/logo.png": ["public"], "private/flag": ["read:backups"]}


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{flag-unavailable-in-dev}"


def _server_fetch(url):
    from urllib.parse import urlparse

    p = urlparse(url)
    if p.hostname in ("127.0.0.1", "localhost") and p.path == "/internal/sts":
        return {"token": _TOKEN, "scope": "read:backups"}
    return {"note": "external fetch ok"}


@app.route("/")
def index():
    return jsonify(
        {
            "service": "vaultboard",
            "fetch": "/fetch?url=",
            "object": "/object?key=&token=",
        }
    )


@app.route("/fetch")
def fetch():
    return jsonify({"result": _server_fetch(request.args.get("url", ""))})


@app.route("/object")
def obj():
    key = request.args.get("key", "")
    token = request.args.get("token", "")
    if key not in ACL:
        return jsonify({"error": "no such object"}), 404
    scope = "read:backups" if token == _TOKEN else "public"
    if scope not in ACL[key]:
        return jsonify({"error": "forbidden for scope " + scope}), 403
    body = _flag() if key == "private/flag" else "<bytes>"
    return jsonify({"key": key, "body": body})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
