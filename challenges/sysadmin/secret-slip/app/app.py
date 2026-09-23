"""Secret Slip — a key-rotation service that leaks its pending rotation nonce.

Design (served challenge, per-team flag):

  * The rotation controller holds a secret ``pending_nonce`` that authorises the
    next admin-key rotation. ``/status`` accidentally includes that nonce in its
    JSON (a state leak that should never ship).
  * ``/rotate`` accepts the pending nonce and rotates the admin key, returning
    the freshly minted admin token to whoever triggered it. Because the nonce
    leaked, an attacker triggers the rotation and receives the new admin token.
  * ``/admin/flag`` returns the instance flag to a valid admin token.

Intended path: read ``pending_nonce`` from ``/status`` → ``/rotate`` with it →
receive the admin token → ``/admin/flag``.

The flag at ``/flag.txt`` is served only behind a valid admin token, which the
leaked-nonce rotation hands to the attacker.
"""
import os
import secrets

from flask import Flask, jsonify, request

app = Flask(__name__)

STATE = {
    "rotation": 1,
    "pending_nonce": secrets.token_hex(16),  # BUG: leaked by /status
    "admin_token": secrets.token_urlsafe(24),
}


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{flag-unavailable-in-dev}"


@app.route("/")
def index():
    return jsonify(
        {
            "service": "secret-slip",
            "status": "/status",
            "rotate": "POST /rotate {nonce}",
            "admin_flag": "/admin/flag  (X-Admin-Token)",
        }
    )


@app.route("/status")
def status():
    # BUG: the pending rotation nonce is secret but is dumped here.
    return jsonify(
        {"rotation": STATE["rotation"], "pending_nonce": STATE["pending_nonce"]}
    )


@app.route("/rotate", methods=["POST"])
def rotate():
    body = request.get_json(silent=True) or {}
    if body.get("nonce") != STATE["pending_nonce"]:
        return jsonify({"error": "bad rotation nonce"}), 403
    STATE["rotation"] += 1
    STATE["admin_token"] = secrets.token_urlsafe(24)
    STATE["pending_nonce"] = secrets.token_hex(16)
    return jsonify({"rotated": STATE["rotation"], "admin_token": STATE["admin_token"]})


@app.route("/admin/flag")
def admin_flag():
    if request.headers.get("X-Admin-Token") != STATE["admin_token"]:
        return jsonify({"error": "admin only"}), 403
    return jsonify({"flag": _flag()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
