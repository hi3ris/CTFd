"""Schedd Systemd — a root unit whose ExecStart honours caller-set environment.

Design (served challenge, per-team flag):

  * A systemd unit ``backup.service`` runs as root. Its ``ExecStart`` is
    ``backup-helper $BACKUP_ARGS`` and the unit reads a drop-in environment file
    the operators let unprivileged users edit (to tweak ``LOG_LEVEL``).
  * ``/set-env`` writes any key into that drop-in with no allow-list, so an
    attacker sets ``BACKUP_ARGS``. ``/start`` runs the unit as root;
    ``backup-helper`` honours ``--dump-secrets`` (a dev flag left enabled), which
    reads the instance secret.

Intended path: read ``/unit`` (shows the helper usage incl. ``--dump-secrets``)
→ ``/set-env BACKUP_ARGS=--dump-secrets`` → ``/start``.

The flag at ``/flag.txt`` is root-owned and served by no route; it only appears
as the output of the root unit the attacker steered via injected env.
"""
import os

from flask import Flask, jsonify, request

app = Flask(__name__)

# Unit environment drop-in (operators only meant LOG_LEVEL to be user-editable).
UNIT_ENV = {"LOG_LEVEL": "info"}


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{flag-unavailable-in-dev}"


def backup_helper(args):
    # dev flag left enabled in the shipped helper
    if "--dump-secrets" in args.split():
        return _flag()
    return "backup-helper: ok"


@app.route("/")
def index():
    return jsonify(
        {
            "service": "auditd-systemd",
            "unit": "/unit",
            "set_env": "POST /set-env {key, value}",
            "start": "/start",
        }
    )


@app.route("/unit")
def unit():
    return jsonify(
        {
            "unit": "backup.service (User=root)",
            "ExecStart": "backup-helper $BACKUP_ARGS",
            "helper_usage": "backup-helper [--log] [--dump-secrets(dev)]",
            "env": UNIT_ENV,
        }
    )


@app.route("/set-env", methods=["POST"])
def set_env():
    body = request.get_json(silent=True) or {}
    key = body.get("key")
    if not key:
        return jsonify({"error": "key required"}), 400
    # BUG: no allow-list — BACKUP_ARGS (and anything else) can be injected.
    UNIT_ENV[key] = body.get("value", "")
    return jsonify({"env": UNIT_ENV})


@app.route("/start")
def start():
    return jsonify(
        {
            "started": "backup.service",
            "output": backup_helper(UNIT_ENV.get("BACKUP_ARGS", "")),
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
