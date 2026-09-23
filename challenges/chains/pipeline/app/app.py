"""Pipeline — a chain: dependency confusion → build hook → runner RCE.

Design (served challenge, per-team flag):

  Stage 1: ``internal-lib`` is pinned in the lockfile to the private registry at
    ``1.0.0``, but ``/build`` resolves the highest version across the private and
    a public registry. ``/publish-public`` lets anyone register a higher public
    version — dependency confusion.
  Stage 2: ``/build`` runs the winning package's build hook. A hook of the form
    ``install-runner:<action>`` installs a runner action.
  Stage 3: ``/run`` executes the installed runner action as the CI runner; the
    ``emit-flag`` action reads the instance secret.

Each stage unlocks the next as an effect. The flag at ``/flag.txt`` is served by
no route.
"""
import os

from flask import Flask, jsonify, request

app = Flask(__name__)

PRIVATE = {"internal-lib": {"version": "1.0.0", "buildhook": "log:build ok"}}
PUBLIC = {}
RUNNER = {"action": None}


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{flag-unavailable-in-dev}"


def _ver(v):
    return tuple(int(x) for x in v.split("."))


@app.route("/")
def index():
    return jsonify(
        {
            "service": "pipeline",
            "publish_public": "POST /publish-public {name,version,buildhook}",
            "build": "POST /build {name}",
            "run": "POST /run",
            "lockfile": {"internal-lib": PRIVATE["internal-lib"]["version"]},
        }
    )


@app.route("/publish-public", methods=["POST"])
def publish_public():
    b = request.get_json(silent=True) or {}
    if not b.get("name") or not b.get("version"):
        return jsonify({"error": "name and version required"}), 400
    PUBLIC[b["name"]] = {"version": b["version"], "buildhook": b.get("buildhook", "")}
    return jsonify({"published": b["name"], "version": b["version"]})


@app.route("/build", methods=["POST"])
def build():
    b = request.get_json(silent=True) or {}
    name = b.get("name", "internal-lib")
    priv, pub = PRIVATE.get(name), PUBLIC.get(name)
    winner, src = priv, "private"
    if pub and (not priv or _ver(pub["version"]) > _ver(priv["version"])):
        winner, src = pub, "public"
    if not winner:
        return jsonify({"error": "unresolved"}), 404
    hook = winner["buildhook"]
    if hook.startswith("install-runner:"):
        RUNNER["action"] = hook.split(":", 1)[1]
        return jsonify({"source": src, "build": "runner installed"})
    return jsonify({"source": src, "build": hook})


@app.route("/run", methods=["POST"])
def run():
    action = RUNNER["action"]
    if action == "emit-flag":
        return jsonify({"ran": action, "output": _flag()})
    if action is None:
        return jsonify({"error": "no runner installed"}), 400
    return jsonify({"ran": action, "output": f"ran: {action}"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
