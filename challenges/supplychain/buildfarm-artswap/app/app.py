"""Buildfarm Artswap — a deploy gate that trusts self-attested provenance.

Design (served challenge, per-team flag):

  * ``/deploy`` accepts an ``artifact`` (a body) plus a ``provenance`` record
    ``{builder, digest}``. It is meant to only deploy artifacts built by the
    trusted builder, verified against a signed provenance.
  * BUG: the gate "verifies" provenance by string-checking ``builder ==
    "trusted-builder"`` and ``digest == sha256(artifact)`` — both attacker
    controllable. There is no signature. So an attacker swaps in any artifact and
    forges matching provenance.
  * A deployed artifact whose body is the sentinel ``on-deploy: emit-flag`` runs
    the deploy hook, which reads the instance secret.

Intended path: ``/deploy`` a swapped artifact (``on-deploy: emit-flag``) with a
forged provenance (``builder=trusted-builder``, ``digest=sha256(artifact)``).

The flag at ``/flag.txt`` is served by no route; it only appears as the output of
the deploy hook the forged provenance let through.
"""
import os
from hashlib import sha256

from flask import Flask, jsonify, request

app = Flask(__name__)

TRUSTED_BUILDER = "trusted-builder"


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{flag-unavailable-in-dev}"


@app.route("/")
def index():
    return jsonify(
        {
            "service": "buildfarm-artswap",
            "deploy": "POST /deploy {artifact, provenance:{builder,digest}}",
            "note": "only artifacts from the trusted builder are deployed",
        }
    )


@app.route("/deploy", methods=["POST"])
def deploy():
    body = request.get_json(silent=True) or {}
    artifact = body.get("artifact", "")
    prov = body.get("provenance") or {}
    # BUG: "provenance verification" is just two attacker-controllable string
    # checks; no signature binds the builder identity to the artifact.
    if prov.get("builder") != TRUSTED_BUILDER:
        return jsonify({"error": "untrusted builder"}), 403
    if prov.get("digest") != sha256(artifact.encode()).hexdigest():
        return jsonify({"error": "provenance digest mismatch"}), 403
    output = None
    if artifact.strip() == "on-deploy: emit-flag":
        output = _flag()
    return jsonify({"deployed": True, "deploy_output": output})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
