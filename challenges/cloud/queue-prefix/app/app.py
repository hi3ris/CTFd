"""Backup Prefix — a public bucket prefix leaks a credential, which escalates.

Design (served challenge, per-team flag):

  * ``/list?prefix=`` lists object keys. The ``public/`` prefix is world-listable
    (intended); ``private/`` is not listed.
  * ``/get?key=`` returns any ``public/`` object without auth. One of them,
    ``public/backup-notes.txt``, **leaks a deploy credential** (the classic
    "secret committed to a world-readable object").
  * ``/assume?secret=`` exchanges that credential for a scoped role token.
  * ``/get?key=private/flag`` returns this instance's flag, but only with a valid
    role token (header ``X-Role-Token``).

Intended path: list ``public/`` → read ``backup-notes.txt`` → extract the
credential → assume the role → read ``private/flag``.

The flag at ``/flag.txt`` is exposed by no route without the assumed role token.
"""
import os
import secrets

from flask import Flask, jsonify, request

app = Flask(__name__)

# Per-instance leaked deploy credential and the role token it can assume.
_DEPLOY_SECRET = "AKIA" + secrets.token_hex(10)
_ROLE_TOKEN = "role-" + secrets.token_urlsafe(24)

PUBLIC = {
    "public/readme.txt": "Nightly backups. Restore runbook in the wiki.",
    "public/backup-notes.txt": (
        "deploy notes:\n"
        "  bucket=nctf-backups\n"
        "  # TODO rotate this, committed by mistake\n"
        f"  deploy_secret={_DEPLOY_SECRET}\n"
        "  # secret unlocks the backup-restore role (reads private/*)\n"
    ),
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
            "service": "queue-prefix",
            "list": "/list?prefix=public/",
            "get": "/get?key=...  (private keys need X-Role-Token)",
            "assume": "/assume?secret=...  -> role token",
        }
    )


@app.route("/list")
def list_keys():
    prefix = request.args.get("prefix", "")
    if not prefix.startswith("public/"):
        return jsonify({"error": "only the public/ prefix is listable"}), 403
    return jsonify({"keys": [k for k in PUBLIC if k.startswith(prefix)]})


@app.route("/assume")
def assume():
    if not secrets.compare_digest(request.args.get("secret", ""), _DEPLOY_SECRET):
        return jsonify({"error": "bad credential"}), 401
    return jsonify({"role": "backup-restore", "token": _ROLE_TOKEN})


@app.route("/get")
def get():
    key = request.args.get("key", "")
    if key in PUBLIC:
        return jsonify({"key": key, "body": PUBLIC[key]})
    if key == "private/flag":
        token = request.headers.get("X-Role-Token", "")
        if not secrets.compare_digest(token, _ROLE_TOKEN):
            return jsonify({"error": "private object: role token required"}), 403
        return jsonify({"key": key, "body": _flag()})
    return jsonify({"error": "no such object"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
