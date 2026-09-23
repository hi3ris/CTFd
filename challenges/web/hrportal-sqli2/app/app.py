#!/usr/bin/env python3
"""Forum SQLi2 — a second-order SQL injection.

Design (served challenge, per-team flag):

  * ``/register`` and ``/login`` store and check the username with **parameterised
    queries** — safe. So a naive first-order injection at the login form fails.
  * ``/dashboard`` looks up the logged-in user's stored name and then builds a
    second query by **string-formatting that name into SQL** — the second-order
    flaw. The name was attacker-chosen at registration.
  * The per-team flag lives in a separate ``secret`` table, reachable only through
    that injected query.

Intended path: register a username that is a UNION payload
(`zzz' UNION SELECT flag FROM secret-- -`), log in with it (parameterised login
matches the stored row exactly), then open ``/dashboard`` — the stored payload is
now interpolated into SQL and the UNION returns the flag.

The flag at ``/flag.txt`` is loaded into ``secret`` and returned by no route
except through this injection.
"""
import os
import secrets
import sqlite3

from flask import Flask, jsonify, request

app = Flask(__name__)
_SESSIONS = {}


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{flag-unavailable-in-dev}"


# One in-memory DB for the whole process so registrations persist across requests.
_SHARED = sqlite3.connect(":memory:", check_same_thread=False)
_SHARED.execute(
    "CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT, pass TEXT, role TEXT)"
)
_SHARED.execute("CREATE TABLE secret(flag TEXT)")
_SHARED.execute("INSERT INTO secret(flag) VALUES (?)", (_flag(),))
_SHARED.execute(
    "INSERT INTO users(name, pass, role) VALUES ('admin', ?, 'admin')",
    (secrets.token_hex(16),),
)
_SHARED.commit()


@app.route("/")
def index():
    return jsonify(
        {
            "service": "hrportal-sqli2",
            "register": "/register?user=X&pass=Y",
            "login": "/login?user=X&pass=Y -> sid",
            "dashboard": "/dashboard?sid=... -> your role",
        }
    )


@app.route("/register")
def register():
    user = request.args.get("user", "")
    pw = request.args.get("pass", "")
    if not user or not pw:
        return jsonify({"error": "user and pass required"}), 400
    # Safe: parameterised insert. The username is stored verbatim.
    _SHARED.execute(
        "INSERT INTO users(name, pass, role) VALUES (?, ?, 'user')", (user, pw)
    )
    _SHARED.commit()
    return jsonify({"ok": True, "user": user})


@app.route("/login")
def login():
    user = request.args.get("user", "")
    pw = request.args.get("pass", "")
    # Safe: parameterised. Matches the row whose name equals the exact string.
    row = _SHARED.execute(
        "SELECT id, name FROM users WHERE name = ? AND pass = ?", (user, pw)
    ).fetchone()
    if not row:
        return jsonify({"error": "bad credentials"}), 401
    sid = secrets.token_hex(16)
    _SESSIONS[sid] = row[1]  # store the (attacker-chosen) name
    return jsonify({"sid": sid})


@app.route("/dashboard")
def dashboard():
    sid = request.args.get("sid", "")
    name = _SESSIONS.get(sid)
    if name is None:
        return jsonify({"error": "not logged in"}), 401
    # BUG (second order): the stored name is interpolated straight into SQL.
    query = "SELECT role FROM users WHERE name = '%s'" % name
    try:
        rows = _SHARED.execute(query).fetchall()
    except sqlite3.Error as e:
        return jsonify({"error": "query failed", "detail": str(e)}), 400
    return jsonify({"roles": [r[0] for r in rows]})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
