#!/usr/bin/env python3
"""KDF Slip — session tokens keyed by a weak key-derivation.

Design (served challenge, per-team flag):

  * Session tokens are ``HMAC_SHA256(K, username)`` (hex), where the server key
    ``K = SHA256(b"nctf-kdf-" + seed)`` and ``seed`` is a **4-digit PIN** chosen
    at boot. That is the weak KDF: only 10 000 possible keys.
  * ``/login`` hands you a valid *guest* token — i.e. one known plaintext/MAC
    pair under the unknown key.
  * ``/panel?user=admin&token=...`` returns this instance's flag for a valid
    ``admin`` token.

Intended path: take the guest token, brute-force the 4-digit seed offline (for
each candidate derive ``K`` and check ``HMAC(K,"guest")`` against the observed
token), recover ``K``, forge ``HMAC(K,"admin")``, and open ``/panel`` as admin.

The flag at ``/flag.txt`` is exposed by no route other than this admin-token check.
"""
import hashlib
import hmac
import os

from flask import Flask, jsonify, request

app = Flask(__name__)

# 4-digit seed -> 10k-key space. Weak by construction (this is the vuln).
_SEED = f"{int.from_bytes(os.urandom(2), 'big') % 10000:04d}"
_K = hashlib.sha256(b"nctf-kdf-" + _SEED.encode()).digest()


def token_for(user: str) -> str:
    return hmac.new(_K, user.encode(), hashlib.sha256).hexdigest()


@app.route("/")
def index():
    return jsonify(
        {
            "service": "sealbox-kdf",
            "login": "/login -> guest token",
            "panel": "/panel?user=admin&token=HEX",
            "note": "server key = SHA256('nctf-kdf-' + 4-digit-seed)",
        }
    )


@app.route("/login")
def login():
    return jsonify({"user": "guest", "token": token_for("guest")})


@app.route("/panel")
def panel():
    user = request.args.get("user", "")
    tok = request.args.get("token", "")
    if not hmac.compare_digest(tok, token_for(user)):
        return jsonify({"error": "bad token"}), 401
    if user != "admin":
        return jsonify({"role": user, "note": "no flag for this user"}), 403
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return jsonify({"flag": fh.read().strip()})
    except OSError:
        return jsonify({"error": "flag unavailable"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
