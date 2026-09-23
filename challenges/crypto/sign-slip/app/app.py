"""Sign Slip — a token "signature" that is just a checksum, not a MAC.

Design (served challenge, per-team flag):

  * ``/login`` issues a session token ``role=<r>;sig=<crc32(role)>``. The server
    calls this a signed token, but the "signature" is a plain CRC32 of the role
    — no secret is involved, so anyone can compute a valid sig for any role.
  * ``/whoami`` verifies ``sig == crc32(role)`` and trusts the role.
  * ``/admin/flag`` returns the instance flag when the presented token's role is
    ``admin``.

Intended path: forge ``role=admin;sig=<crc32("admin")>`` and present it.

The flag at ``/flag.txt`` is served only to an admin token, which the forged
checksum grants.
"""
import os
from zlib import crc32

from flask import Flask, jsonify, request

app = Flask(__name__)


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{flag-unavailable-in-dev}"


def _sig(role):
    # NOT a MAC: a keyless checksum, so it is trivially forgeable.
    return format(crc32(role.encode()) & 0xFFFFFFFF, "08x")


def _parse(token):
    parts = dict(p.split("=", 1) for p in token.split(";") if "=" in p)
    return parts.get("role", ""), parts.get("sig", "")


@app.route("/")
def index():
    return jsonify(
        {
            "service": "sign-slip",
            "login": "/login  -> token",
            "whoami": "/whoami  (X-Token)",
            "admin_flag": "/admin/flag  (X-Token)",
        }
    )


@app.route("/login")
def login():
    role = "user"
    return jsonify({"token": f"role={role};sig={_sig(role)}"})


@app.route("/whoami")
def whoami():
    role, sig = _parse(request.headers.get("X-Token", ""))
    if sig != _sig(role):
        return jsonify({"error": "bad signature"}), 403
    return jsonify({"role": role})


@app.route("/admin/flag")
def admin_flag():
    role, sig = _parse(request.headers.get("X-Token", ""))
    if sig != _sig(role):
        return jsonify({"error": "bad signature"}), 403
    if role != "admin":
        return jsonify({"error": "admin only"}), 403
    return jsonify({"flag": _flag()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
