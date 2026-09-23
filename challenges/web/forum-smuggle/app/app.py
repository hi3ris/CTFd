"""CMS Smuggle — a naive ingest parser that processes a pipelined smuggled request.

Design (served challenge, per-team flag):

  * The frontend caches page responses by path (``/page?p=``). ``/admin/flag`` is
    admin-only and returns 403 to ordinary callers.
  * ``/ingest`` accepts a raw body. Its hand-rolled parser splits the body and
    treats a trailing ``SMUGGLED GET <path>`` line as a *second, pipelined*
    request — and processes it with internal (trusted) privileges, caching its
    response under ``<path>``. This models a CL/TE desync: the backend sees a
    request the frontend never authorised.
  * The attacker smuggles ``GET /admin/flag``; its admin response is cached, then
    read back from the cache.

Intended path: ``/ingest`` a body containing ``SMUGGLED GET /admin/flag`` →
``/page?p=/admin/flag`` returns the poisoned (admin) response.

The flag at ``/flag.txt`` is served only to the internal/trusted request the
smuggling forges.
"""
import os

from flask import Flask, jsonify, request

app = Flask(__name__)

CACHE = {}


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{flag-unavailable-in-dev}"


def _handle_internal(path):
    # Backend handling a trusted (internal) request.
    if path == "/admin/flag":
        return _flag()
    return f"internal: {path}"


@app.route("/")
def index():
    return jsonify(
        {
            "service": "forum-smuggle",
            "ingest": "POST /ingest  (raw body)",
            "page": "/page?p=<path>  (cache)",
            "admin_flag": "/admin/flag  (admin only)",
        }
    )


@app.route("/ingest", methods=["POST"])
def ingest():
    body = request.get_data(as_text=True)
    poisoned = []
    for line in body.splitlines():
        line = line.strip()
        # BUG: a smuggled pipelined request is parsed and served as trusted.
        if line.startswith("SMUGGLED GET "):
            path = line[len("SMUGGLED GET ") :].strip()
            CACHE[path] = _handle_internal(path)
            poisoned.append(path)
    return jsonify({"ingested": True, "cache_poisoned": poisoned})


@app.route("/page")
def page():
    p = request.args.get("p", "")
    if p in CACHE:
        return jsonify({"path": p, "cached": CACHE[p]})
    return jsonify({"path": p, "cached": None})


@app.route("/admin/flag")
def admin_flag():
    # Direct external access is not admin.
    return jsonify({"error": "admin only"}), 403


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
