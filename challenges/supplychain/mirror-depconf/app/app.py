"""Buildfarm Depconf — a resolver that prefers a higher public version.

Design (served challenge, per-team flag):

  * An internal dependency ``internal-lib`` is pinned in the lockfile to the
    private registry at ``1.0.0``. The resolver, however, also queries a public
    registry and **picks whichever version is higher** — classic dependency
    confusion.
  * ``/publish-public`` lets anyone register a public package + version + build
    hook. Publishing ``internal-lib`` at a version above ``1.0.0`` makes the
    resolver choose the attacker's package.
  * ``/resolve?name=`` resolves the dependency and runs the winning package's
    build hook. The ``emit-flag`` build hook reads the instance secret.

Intended path: ``/publish-public`` ``internal-lib`` at a high version with build
hook ``emit-flag`` → ``/resolve?name=internal-lib`` runs it.

The flag at ``/flag.txt`` is served by no route; it only appears as the output of
the build hook the confused resolver ran.
"""
import os

from flask import Flask, jsonify, request

app = Flask(__name__)

# Private registry: the intended source, pinned in the lockfile.
PRIVATE = {"internal-lib": {"version": "1.0.0", "buildhook": "log:build internal-lib"}}
# Public registry: attacker-writable.
PUBLIC = {}


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{flag-unavailable-in-dev}"


def _ver(v):
    return tuple(int(x) for x in v.split("."))


def run_hook(hook):
    if hook == "emit-flag":
        return _flag()
    if hook.startswith("log:"):
        return hook[4:]
    return f"ran: {hook}"


@app.route("/")
def index():
    return jsonify(
        {
            "service": "mirror-depconf",
            "resolve": "/resolve?name=internal-lib",
            "publish_public": "POST /publish-public {name, version, buildhook}",
            "lockfile": {"internal-lib": PRIVATE["internal-lib"]["version"]},
        }
    )


@app.route("/publish-public", methods=["POST"])
def publish_public():
    body = request.get_json(silent=True) or {}
    name = body.get("name")
    version = body.get("version")
    if not name or not version:
        return jsonify({"error": "name and version required"}), 400
    PUBLIC[name] = {"version": version, "buildhook": body.get("buildhook", "")}
    return jsonify({"published": name, "version": version})


@app.route("/resolve")
def resolve():
    name = request.args.get("name", "")
    priv = PRIVATE.get(name)
    pub = PUBLIC.get(name)
    # BUG: pick the highest version across BOTH registries.
    winner, src = priv, "private"
    if pub and (not priv or _ver(pub["version"]) > _ver(priv["version"])):
        winner, src = pub, "public"
    if not winner:
        return jsonify({"error": "unresolved"}), 404
    output = run_hook(winner["buildhook"])
    return jsonify(
        {"name": name, "source": src, "version": winner["version"], "build": output}
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
