"""Ingestd Envreuse — a debug endpoint leaks the worker's task-signing secret.

Design (served challenge, per-team flag):

  * ``/debug/env`` dumps the process environment "for troubleshooting" —
    including ``WORKER_HMAC_SECRET``, the key the task runner uses to authorise
    commands. It should never have been exposed.
  * ``/task`` runs a command only if it carries a valid ``sig = HMAC(secret,
    cmd)``. With the leaked secret an attacker signs any command; the ``emit-
    flag`` command reads the instance secret.

Intended path: read ``WORKER_HMAC_SECRET`` from ``/debug/env`` → sign the
``emit-flag`` command → ``/task``.

The flag at ``/flag.txt`` is served by no route; it only appears as the output of
the signed command the attacker forged with the leaked secret.
"""
import hmac
import os
from hashlib import sha256

from flask import Flask, jsonify, request

app = Flask(__name__)

# Per-instance worker secret. Leaked by the debug endpoint (the bug).
WORKER_HMAC_SECRET = os.environ.get("WORKER_HMAC_SECRET") or os.urandom(12).hex()


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{flag-unavailable-in-dev}"


def _sign(cmd):
    return hmac.new(WORKER_HMAC_SECRET.encode(), cmd.encode(), sha256).hexdigest()


def run_cmd(cmd):
    if cmd == "emit-flag":
        return _flag()
    return f"ran: {cmd}"


@app.route("/")
def index():
    return jsonify(
        {
            "service": "ingestd-envreuse",
            "task": "POST /task {cmd, sig}",
            "note": "tasks must be signed with the worker secret",
        }
    )


@app.route("/debug/env")
def debug_env():
    # BUG: dumps sensitive env, including the worker signing secret.
    return jsonify(
        {
            "env": {
                "LOG_LEVEL": "info",
                "REGION": "eu-west",
                "WORKER_HMAC_SECRET": WORKER_HMAC_SECRET,
            }
        }
    )


@app.route("/task", methods=["POST"])
def task():
    body = request.get_json(silent=True) or {}
    cmd = body.get("cmd", "")
    sig = body.get("sig", "")
    if not hmac.compare_digest(sig, _sign(cmd)):
        return jsonify({"error": "bad signature"}), 403
    return jsonify({"cmd": cmd, "output": run_cmd(cmd)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
