"""Backup Presign — a presigned-URL issuer that fails to scope the key prefix.

Design (served challenge, per-team flag):

  * ``/presign?key=`` returns a presigned PUT URL: ``/put?key=..&exp=..&sig=..``
    where ``sig = HMAC(server_secret, "PUT|key|exp")``. The issuer is *meant* to
    only sign keys under ``uploads/`` (that is the documented, user-writable
    prefix) — but it signs **whatever key you ask for**, including the
    privileged ``hooks/`` prefix the deploy worker trusts.
  * ``/put?key=&exp=&sig=`` writes a body to the object store iff the signature
    verifies and has not expired. No prefix check here either — it trusts the
    presigned URL.
  * ``/deploy`` runs the post-deploy step: it reads ``hooks/postdeploy`` from the
    store and, if that object is the sentinel ``emit-flag``, writes this
    instance's flag into the readable ``artifacts/deploy.log`` object. This
    models "the presigned write executes at deploy time".
  * ``/get?key=`` returns any object in the store (so the attacker can read back
    ``artifacts/deploy.log`` once deploy has run).

Intended path: presign a PUT for ``hooks/postdeploy`` (a prefix the issuer
should have refused) → PUT the ``emit-flag`` sentinel → trigger ``/deploy`` →
read ``artifacts/deploy.log``.

The flag at ``/flag.txt`` is served by no route; it only reaches the attacker
through the deploy step they triggered.
"""
import hmac
import os
import time
from hashlib import sha256

from flask import Flask, jsonify, request

app = Flask(__name__)

# Per-instance signing secret for presigned URLs (never leaves the server).
_SIGN_SECRET = os.urandom(16)

# Object store. Seeded with the documented, user-writable uploads prefix; the
# privileged hooks/ prefix is consumed by /deploy and must not be user-writable.
STORE = {"uploads/README.txt": "Drop build artifacts under uploads/."}

# The prefix the presign issuer is *supposed* to restrict signing to.
INTENDED_PREFIX = "uploads/"


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{flag-unavailable-in-dev}"


def _sign(method, key, exp):
    msg = f"{method}|{key}|{exp}".encode()
    return hmac.new(_SIGN_SECRET, msg, sha256).hexdigest()


@app.route("/")
def index():
    return jsonify(
        {
            "service": "identity-presign",
            "presign": "/presign?key=uploads/<name>  -> presigned PUT url",
            "put": "/put?key=&exp=&sig=  (body is the object)",
            "deploy": "/deploy  -> runs hooks/postdeploy",
            "get": "/get?key=...",
        }
    )


@app.route("/presign")
def presign():
    key = request.args.get("key", "")
    if not key:
        return jsonify({"error": "key required"}), 400
    # BUG: the documented contract restricts signing to uploads/, but the issuer
    # never enforces INTENDED_PREFIX — it signs any key it is handed.
    exp = int(time.time()) + 300
    sig = _sign("PUT", key, exp)
    return jsonify({"url": f"/put?key={key}&exp={exp}&sig={sig}"})


@app.route("/put", methods=["PUT", "POST"])
def put():
    key = request.args.get("key", "")
    exp = request.args.get("exp", "")
    sig = request.args.get("sig", "")
    try:
        exp_i = int(exp)
    except ValueError:
        return jsonify({"error": "bad exp"}), 400
    if exp_i < int(time.time()):
        return jsonify({"error": "url expired"}), 403
    if not hmac.compare_digest(sig, _sign("PUT", key, exp)):
        return jsonify({"error": "bad signature"}), 403
    STORE[key] = request.get_data(as_text=True)
    return jsonify({"ok": True, "key": key})


@app.route("/deploy")
def deploy():
    # Post-deploy worker: a trusted hook, if present, runs. Here "running" the
    # emit-flag hook publishes the flag into a readable artifact.
    hook = STORE.get("hooks/postdeploy", "")
    if hook.strip() == "emit-flag":
        STORE["artifacts/deploy.log"] = "post-deploy hook ran: " + _flag()
        return jsonify({"deployed": True, "hook": "ran"})
    return jsonify({"deployed": True, "hook": "none"})


@app.route("/get")
def get():
    key = request.args.get("key", "")
    if key in STORE:
        return jsonify({"key": key, "body": STORE[key]})
    return jsonify({"error": "not found"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
