#!/usr/bin/env python3
"""Sealbox Signext — a MAC built as SHA256(secret || message), length-extendable.

Design (served challenge, per-team flag):

  * ``/sign?cmd=X`` returns a signed command ``msg = "user=guest&cmd=<X>"`` with
    ``sig = SHA256(secret || msg)``. It refuses any cmd containing ``op`` or
    ``grantflag`` — you cannot ask it to sign the privileged command.
  * ``/api?msg=HEX&sig=HEX`` recomputes ``SHA256(secret || msg)`` and, if it
    matches and ``msg`` ends with the privileged suffix ``&op=grantflag``,
    returns this instance's flag.

Because the MAC is ``SHA256(secret || message)`` (not HMAC), it is vulnerable to a
**length-extension attack**: from a valid ``(msg, sig)`` an attacker computes the
MAC of ``msg || glue-padding || &op=grantflag`` without knowing the secret. The
secret length is unknown, so the attacker brute-forces it.

The flag at ``/flag.txt`` is returned by no route other than the ``/api`` check.
"""
import hashlib
import os
import secrets

from flask import Flask, jsonify, request

app = Flask(__name__)

# Secret of unknown (to the player) length; the attack brute-forces the length.
_SECRET = secrets.token_bytes(8 + secrets.randbelow(17))  # 8..24 bytes
PRIV_SUFFIX = b"&op=grantflag"


def mac(msg: bytes) -> str:
    return hashlib.sha256(_SECRET + msg).hexdigest()


@app.route("/")
def index():
    return jsonify(
        {
            "service": "sessiond-signext",
            "sign": "/sign?cmd=X  -> msg + sig  (refuses op/grantflag)",
            "api": "/api?msg=HEX&sig=HEX  (needs suffix &op=grantflag)",
            "mac": "sig = SHA256(secret || msg)",
        }
    )


@app.route("/sign")
def sign():
    cmd = request.args.get("cmd", "")
    if "op" in cmd or "grantflag" in cmd:
        return jsonify({"error": "refused: privileged command"}), 403
    msg = ("user=guest&cmd=" + cmd).encode()
    return jsonify({"msg": msg.hex(), "sig": mac(msg)})


@app.route("/api")
def api():
    try:
        msg = bytes.fromhex(request.args.get("msg", ""))
    except ValueError:
        return jsonify({"error": "msg must be hex"}), 400
    sig = request.args.get("sig", "")
    if not secrets.compare_digest(sig, mac(msg)):
        return jsonify({"error": "bad signature"}), 401
    if not msg.endswith(PRIV_SUFFIX):
        return jsonify({"error": "signature valid, but not a grantflag command"}), 403
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return jsonify({"flag": fh.read().strip()})
    except OSError:
        return jsonify({"error": "flag unavailable"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
