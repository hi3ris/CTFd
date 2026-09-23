"""Buildfarm Postinstall — an installer that runs any published package's hook.

Design (served challenge, per-team flag):

  * ``/publish`` registers a package ``{name, postinstall}`` with no signing or
    review — the registry trusts whoever publishes.
  * ``/install?pkg=`` fetches a package and runs its ``postinstall`` hook. Hooks
    are dispatched through a small runner; the ``emit-flag`` hook (a debug hook
    that should not be reachable) reads the instance secret.
  * Because publishing is unauthenticated, an attacker publishes a package whose
    post-install hook is ``emit-flag`` and installs it.

Intended path: ``/publish`` a package with ``postinstall=emit-flag`` →
``/install`` it → read the flag from the install log.

The flag at ``/flag.txt`` is served by no route; it only appears as the output of
the post-install hook the attacker planted.
"""
import os

from flask import Flask, jsonify, request

app = Flask(__name__)

# name -> postinstall hook string. Seeded with a benign package.
PACKAGES = {"hello-lib": "log:installed hello-lib"}


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{flag-unavailable-in-dev}"


def run_hook(hook):
    # Minimal post-install runner. `emit-flag` is a debug hook left enabled.
    if hook == "emit-flag":
        return _flag()
    if hook.startswith("log:"):
        return hook[4:]
    return f"ran: {hook}"


@app.route("/")
def index():
    return jsonify(
        {
            "service": "buildfarm-postinstall",
            "publish": "POST /publish {name, postinstall}",
            "install": "/install?pkg=name",
            "packages": sorted(PACKAGES),
        }
    )


@app.route("/publish", methods=["POST"])
def publish():
    body = request.get_json(silent=True) or {}
    name = body.get("name")
    if not name:
        return jsonify({"error": "name required"}), 400
    # BUG: no signature / no review — anyone can register a package + hook.
    PACKAGES[name] = body.get("postinstall", "")
    return jsonify({"published": name})


@app.route("/install")
def install():
    pkg = request.args.get("pkg", "")
    if pkg not in PACKAGES:
        return jsonify({"error": "no such package"}), 404
    output = run_hook(PACKAGES[pkg])
    return jsonify({"installed": pkg, "postinstall_output": output})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
