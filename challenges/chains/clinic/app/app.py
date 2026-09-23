"""Clinic — a chain: predictable session id → IDOR export → admin action.

Design (served challenge, per-team flag):

  Stage 1: ``/login`` hands every caller a **sequential** session id (1, 2, 3…).
    The admin's session is id 1, created at boot.
  Stage 2: ``/export?sid=`` returns a session's record with **no ownership
    check** (IDOR). Reading session 1 leaks the admin API key.
  Stage 3: ``/admin/rotate`` with that key performs the admin action and returns
    the flag.

Each stage's unlock is an effect of the previous (the leaked key gates the admin
action). The flag at ``/flag.txt`` is served by no route.
"""
import itertools
import os
import secrets

from flask import Flask, jsonify, request

app = Flask(__name__)

_ids = itertools.count(1)
SESSIONS = {}
_ADMIN_KEY = "adm-" + secrets.token_hex(8)


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{flag-unavailable-in-dev}"


def _boot():
    sid = next(_ids)  # id 1: the admin session
    SESSIONS[sid] = {"user": "admin", "role": "admin", "api_key": _ADMIN_KEY}


_boot()


@app.route("/")
def index():
    return jsonify(
        {
            "service": "clinic",
            "login": "POST /login {user}  -> sequential sid",
            "export": "/export?sid=",
            "admin_rotate": "POST /admin/rotate {key}",
        }
    )


@app.route("/login", methods=["POST"])
def login():
    b = request.get_json(silent=True) or {}
    user = b.get("user", "guest")
    sid = next(_ids)
    SESSIONS[sid] = {"user": user, "role": "patient", "api_key": None}
    return jsonify({"sid": sid, "user": user})


@app.route("/export")
def export():
    try:
        sid = int(request.args.get("sid", ""))
    except ValueError:
        return jsonify({"error": "bad sid"}), 400
    # BUG: no ownership check — any session record can be exported (IDOR).
    if sid in SESSIONS:
        return jsonify({"sid": sid, "record": SESSIONS[sid]})
    return jsonify({"error": "not found"}), 404


@app.route("/admin/rotate", methods=["POST"])
def admin_rotate():
    b = request.get_json(silent=True) or {}
    if b.get("key") != _ADMIN_KEY:
        return jsonify({"error": "admin key required"}), 403
    return jsonify({"rotated": True, "flag": _flag()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
