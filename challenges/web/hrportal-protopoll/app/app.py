"""Forum Protopoll — a recursive merge that pollutes a shared config object.

Design (served challenge, per-team flag):

  * ``/settings`` deep-merges user JSON into a shared server-side config with no
    key allow-list. The merge can therefore reach keys the user never should,
    the server-side equivalent of prototype pollution.
  * The renderer consults ``config["render_hook"]`` before serving a page. That
    key is meant to stay empty, but a polluting merge sets it. The ``emit-flag``
    hook reads the instance secret.

Intended path: ``/settings`` merge ``{"render_hook":"emit-flag"}`` → ``/render``
runs the polluted hook.

The flag at ``/flag.txt`` is served by no route; it only appears as the output of
the render hook the pollution enabled.
"""
import os

from flask import Flask, jsonify, request

app = Flask(__name__)

# Shared config template. `render_hook` must never be set by a user.
CONFIG = {"theme": "light", "page_size": 20}


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{flag-unavailable-in-dev}"


def deep_merge(dst, src):
    for k, v in src.items():
        # BUG: no allow-list of merge keys; any key can be introduced/overwritten.
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            deep_merge(dst[k], v)
        else:
            dst[k] = v
    return dst


def run_hook(hook):
    if hook == "emit-flag":
        return _flag()
    return None


@app.route("/")
def index():
    return jsonify(
        {
            "service": "hrportal-protopoll",
            "settings": "POST /settings  (JSON, deep-merged into config)",
            "render": "/render",
        }
    )


@app.route("/settings", methods=["POST"])
def settings():
    body = request.get_json(silent=True) or {}
    deep_merge(CONFIG, body)
    return jsonify({"config_keys": sorted(CONFIG)})


@app.route("/render")
def render():
    out = run_hook(CONFIG.get("render_hook", ""))
    page = {"theme": CONFIG.get("theme"), "rendered": True}
    if out is not None:
        page["hook_output"] = out
    return jsonify(page)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
