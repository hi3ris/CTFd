"""Schedd Cap — a helper binary shipped with an over-broad file capability.

Design (served challenge, per-team flag):

  * ``/bins`` lists the host's helper "binaries" and their Linux capabilities.
    ``logtool`` was granted ``cap_dac_read_search`` (read any file, bypassing
    permissions) so it could tail root-owned logs — far more than it needs.
  * ``/exec?bin=&args=`` runs a helper. Because ``logtool`` carries
    ``cap_dac_read_search``, its ``--read=<path>`` reads any file on the host,
    including the root-only flag.

Intended path: read ``/bins`` → notice ``logtool`` has ``cap_dac_read_search`` →
``/exec?bin=logtool&args=--read=/flag.txt``.

The flag at ``/flag.txt`` is root-owned and served by no route; only the
over-privileged capability lets an unprivileged caller read it.
"""
import os

from flask import Flask, jsonify, request

app = Flask(__name__)

# helper name -> capabilities it was granted (logtool is over-privileged).
BINS = {
    "netcheck": [],
    "logtool": ["cap_dac_read_search"],
    "pstool": [],
}


def _read(path):
    # Models a capability-bearing read: cap_dac_read_search bypasses perms.
    if path == "/flag.txt":
        try:
            with open("/flag.txt", encoding="utf-8") as fh:
                return fh.read().strip()
        except OSError:
            return "NCTF{flag-unavailable-in-dev}"
    return f"<contents of {path}>"


@app.route("/")
def index():
    return jsonify(
        {
            "service": "rotatord-cap",
            "bins": "/bins",
            "exec": "/exec?bin=<name>&args=<args>",
        }
    )


@app.route("/bins")
def bins():
    return jsonify({name: {"caps": caps} for name, caps in BINS.items()})


@app.route("/exec")
def do_exec():
    name = request.args.get("bin", "")
    args = request.args.get("args", "")
    if name not in BINS:
        return jsonify({"error": "no such binary"}), 404
    if args.startswith("--read=") and "cap_dac_read_search" in BINS[name]:
        path = args.split("=", 1)[1]
        return jsonify({"bin": name, "output": _read(path)})
    return jsonify({"bin": name, "output": f"{name}: nothing to do"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
