#!/usr/bin/env python3
"""Forum Authbypass — broken access control -> IDOR -> mass-assignment.

Design (served challenge, per-team flag):

  * ``/register`` creates a user (role=user) and returns a session token.
    ``/me`` reports your server-side role. ``/flag`` returns this instance's flag
    only when your session's role is ``admin``.
  * The admin API (``/admin/users`` and the update endpoint) is "protected" by a
    **client-supplied header** ``X-Account-Role: admin`` — broken access control:
    the server trusts a value the client sets.
  * ``/api/users/<id>`` (GET) is an IDOR: any user is readable with no authz.
  * ``POST /api/users/<id>`` (update) is a **mass-assignment**: it writes every
    field in the body, ``role`` included -- but only past the header gate.

Intended path: register → note your uid → send the update with the forged
``X-Account-Role: admin`` header and ``{"role":"admin"}`` to promote your own
account → ``/flag`` (which checks the real server-side role) returns the flag.

The flag at ``/flag.txt`` is exposed by no route without an admin session.
"""
import os
import secrets

from flask import Flask, jsonify, request

app = Flask(__name__)

USERS = {1: {"id": 1, "name": "administrator", "role": "admin"}}
SESSIONS = {}
_next = [1000]


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{flag-unavailable-in-dev}"


def _admin_header() -> bool:
    # The flaw: authorization decided from a client-controlled header.
    return request.headers.get("X-Account-Role", "").lower() == "admin"


@app.route("/")
def index():
    return jsonify(
        {
            "service": "cms-authbypass",
            "register": "/register?user=X&pass=Y -> token,uid",
            "me": "/me?token=...",
            "users": "/api/users/<id> (GET idor) | POST update",
            "flag": "/flag?token=...  (needs admin session)",
        }
    )


@app.route("/register")
def register():
    user = request.args.get("user", "")
    if not user:
        return jsonify({"error": "user required"}), 400
    uid = _next[0]
    _next[0] += 1
    USERS[uid] = {"id": uid, "name": user, "role": "user"}
    tok = secrets.token_hex(16)
    SESSIONS[tok] = uid
    return jsonify({"token": tok, "uid": uid})


@app.route("/me")
def me():
    uid = SESSIONS.get(request.args.get("token", ""))
    if uid is None:
        return jsonify({"error": "not logged in"}), 401
    return jsonify(USERS[uid])


@app.route("/admin/users")
def admin_users():
    if not _admin_header():
        return jsonify({"error": "admin only"}), 403
    return jsonify({"users": list(USERS.values())})


@app.route("/api/users/<int:uid>", methods=["GET", "POST"])
def api_users(uid):
    if request.method == "GET":
        u = USERS.get(uid)  # IDOR: no authz on read
        return (jsonify(u), 200) if u else (jsonify({"error": "no such user"}), 404)
    # update: gated only by the forgeable header, then mass-assigns every field.
    if not _admin_header():
        return jsonify({"error": "admin only"}), 403
    u = USERS.get(uid)
    if not u:
        return jsonify({"error": "no such user"}), 404
    patch = request.get_json(silent=True) or {}
    for k, v in patch.items():
        if k != "id":
            u[k] = v
    return jsonify(u)


@app.route("/flag")
def flag():
    uid = SESSIONS.get(request.args.get("token", ""))
    if uid is None:
        return jsonify({"error": "not logged in"}), 401
    if USERS[uid]["role"] != "admin":
        return jsonify({"error": "admin only", "role": USERS[uid]["role"]}), 403
    return jsonify({"flag": _flag()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
