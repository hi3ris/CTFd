"""Schedd Cron — a root cron job that resolves its command through a writable PATH.

Design (served challenge, per-team flag):

  * Root's cron runs ``backup`` every tick, resolving the bare name through
    ``$PATH``. The PATH includes a world-writable directory (``/opt/tools``)
    ahead of the system directory — the classic writable-PATH cron misconfig.
  * ``/drop?name=&action=`` writes a helper into the writable dir. ``/run-cron``
    resolves ``backup`` along PATH (first match wins) and runs its action **as
    root**. The ``emit-flag`` action reads the instance secret.

Intended path: drop a ``backup`` helper (action ``emit-flag``) into the writable
PATH dir → trigger the cron run → it runs your helper as root.

The flag at ``/flag.txt`` is root-owned and served by no route; it only appears
as the output of the helper root's cron ran.
"""
import os

from flask import Flask, jsonify, request

app = Flask(__name__)

# PATH as root's cron sees it: the writable dir is (wrongly) ahead of /usr/bin.
PATH_DIRS = ["/opt/tools", "/usr/bin"]
# dir -> {name: action}. /usr/bin ships the real, benign backup.
FS = {"/usr/bin": {"backup": "log:system backup ok"}, "/opt/tools": {}}


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{flag-unavailable-in-dev}"


def run_action(action):
    if action == "emit-flag":
        return _flag()
    if action.startswith("log:"):
        return action[4:]
    return f"ran: {action}"


@app.route("/")
def index():
    return jsonify(
        {
            "service": "schedd-cron",
            "cron": "root runs `backup` via PATH=" + ":".join(PATH_DIRS),
            "drop": "/drop?name=&action=  (writes into /opt/tools)",
            "run": "/run-cron",
        }
    )


@app.route("/drop")
def drop():
    name = request.args.get("name", "")
    action = request.args.get("action", "")
    if not name:
        return jsonify({"error": "name required"}), 400
    # BUG: /opt/tools is world-writable and ahead of /usr/bin on root's PATH.
    FS["/opt/tools"][name] = action
    return jsonify({"dropped": f"/opt/tools/{name}"})


@app.route("/run-cron")
def run_cron():
    # Resolve `backup` along PATH, first match wins, run it as root.
    for d in PATH_DIRS:
        if "backup" in FS.get(d, {}):
            return jsonify(
                {"resolved": f"{d}/backup", "output": run_action(FS[d]["backup"])}
            )
    return jsonify({"error": "backup not found"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
