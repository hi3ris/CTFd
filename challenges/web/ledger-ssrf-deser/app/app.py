"""Ingestd Deser — SSRF into an internal RPC that deserializes untrusted input.

Design (served challenge, per-team flag):

  * ``/fetch?url=`` is a server-side fetcher meant to pull public status pages.
    It does not restrict the target, so it can reach the internal-only RPC
    (``/internal/rpc``) — an SSRF.
  * ``/internal/rpc`` deserializes its body into a registry class with no
    allow-list; the registry still holds a debug ``FlagDumper`` gadget. Direct
    external access to ``/internal/rpc`` is refused (403); only a server-side
    fetch reaches it.

Intended path: SSRF via ``/fetch`` to ``/internal/rpc`` with a poisoned message
``{"__class__":"FlagDumper"}`` → the gadget runs and returns the flag.

The flag at ``/flag.txt`` is served by no route; it only appears as the gadget's
rendered output, reached through the SSRF.
"""
import json
import os

from flask import Flask, jsonify, request

app = Flask(__name__)


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{flag-unavailable-in-dev}"


class Record:
    def __init__(self, value="", **_):
        self.value = value

    def render(self):
        return f"record: {self.value}"


class FlagDumper:
    def __init__(self, **_):
        self.output = _flag()

    def render(self):
        return self.output


REGISTRY = {"Record": Record, "FlagDumper": FlagDumper}


def _rpc(body):
    try:
        msg = json.loads(body or "{}")
    except ValueError:
        return {"error": "bad json"}
    cls = msg.get("__class__", "Record")
    if cls not in REGISTRY:
        return {"error": "unknown class", "registry": sorted(REGISTRY)}
    kwargs = {k: v for k, v in msg.items() if k != "__class__"}
    return {"result": REGISTRY[cls](**kwargs).render()}


def _dispatch(path, body):
    # Server-side (internal) request dispatcher used by /fetch.
    if path in ("/status", "status"):
        return {"status": "ok"}
    if path.rstrip("/").endswith("/internal/rpc") or path == "/internal/rpc":
        return _rpc(body)
    return {"error": "not found"}


@app.route("/")
def index():
    return jsonify(
        {
            "service": "ledger-ssrf-deser",
            "fetch": "/fetch?url=<path>&body=<json>",
            "note": "internal RPC is not reachable directly",
        }
    )


@app.route("/fetch")
def fetch():
    url = request.args.get("url", "")
    body = request.args.get("body")
    # BUG: no allow-list on the fetch target → SSRF to the internal RPC.
    return jsonify(_dispatch(url, body))


@app.route("/internal/rpc", methods=["GET", "POST"])
def internal_rpc():
    # Internal only: refuse direct external calls.
    return jsonify({"error": "internal endpoint; not directly reachable"}), 403


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
