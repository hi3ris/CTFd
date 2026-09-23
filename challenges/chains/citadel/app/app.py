"""Citadel — a 3-stage chain: web foothold → user pivot (reused cred) → root.

Design (served challenge, per-team flag):

  Stage 1 (foothold): ``/login`` still accepts the shipped default deploy
    credentials ``deploy``/``deploy`` and returns a low-privilege ``deploy``
    session token.
  Stage 2 (user pivot): as ``deploy`` you may ``/read`` files under
    ``/home/deploy``. ``/home/deploy/.env`` leaks a *reused* service password.
    ``/su`` to the ``svc`` account with it.
  Stage 3 (root): the ``svc`` account has a sudo rule to run ``flagtool`` as
    root; ``/sudo?cmd=flagtool`` reads the root-only flag.

Each stage's unlock is emitted only as an effect of the previous one (the
session role gates ``/read``/``/su``/``/sudo``). The flag at ``/flag.txt`` is
root-owned and served by no route.
"""
import os
import secrets

from flask import Flask, jsonify, request

app = Flask(__name__)

_SVC_PASSWORD = "svc-" + secrets.token_hex(6)
SESS = {}  # token -> role

FILES = {
    "/home/deploy/.env": (
        "APP_ENV=prod\n"
        f"# reused across deploy+svc by mistake\nsvc_password={_SVC_PASSWORD}\n"
    ),
    "/home/deploy/notes.txt": "remember to rotate the svc password",
}


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{flag-unavailable-in-dev}"


def _role(tok):
    return SESS.get(tok)


@app.route("/")
def index():
    return jsonify(
        {
            "service": "citadel",
            "login": "POST /login {user,pass}",
            "read": "/read?path=  (deploy role, X-Token)",
            "su": "POST /su {user,password}  -> higher role token",
            "sudo": "/sudo?cmd=flagtool  (svc role)",
        }
    )


@app.route("/login", methods=["POST"])
def login():
    b = request.get_json(silent=True) or {}
    if b.get("user") == "deploy" and b.get("pass") == "deploy":
        tok = secrets.token_urlsafe(12)
        SESS[tok] = "deploy"
        return jsonify({"token": tok, "role": "deploy"})
    return jsonify({"error": "bad credentials"}), 401


@app.route("/read")
def read():
    if _role(request.headers.get("X-Token", "")) not in ("deploy", "svc", "root"):
        return jsonify({"error": "login as deploy first"}), 403
    path = request.args.get("path", "")
    if path in FILES:
        return jsonify({"path": path, "body": FILES[path]})
    return jsonify({"error": "not found"}), 404


@app.route("/su", methods=["POST"])
def su():
    b = request.get_json(silent=True) or {}
    if b.get("user") == "svc" and b.get("password") == _SVC_PASSWORD:
        tok = secrets.token_urlsafe(12)
        SESS[tok] = "svc"
        return jsonify({"token": tok, "role": "svc"})
    return jsonify({"error": "su failed"}), 403


@app.route("/sudo")
def sudo():
    if _role(request.headers.get("X-Token", "")) != "svc":
        return jsonify({"error": "svc role required"}), 403
    if request.args.get("cmd") == "flagtool":
        # svc's sudo rule runs flagtool as root.
        return jsonify({"ran": "flagtool", "output": _flag()})
    return jsonify({"error": "command not permitted by sudo rule"}), 403


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
