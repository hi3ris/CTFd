#!/usr/bin/env python3
"""JWT Relay — a homegrown-auth service with an algorithm-confusion flaw.

Design (served challenge, per-team flag):

  * On boot the service generates an RSA key pair. It signs session tokens with
    RS256 and *publishes the public key* at ``/pubkey`` — normal, a client needs
    it to verify tokens offline.
  * The token verifier is homegrown. It reads the ``alg`` header and picks the
    check accordingly, but it feeds the **same ``key`` value** to both branches:
    the RSA public key for RS256, and — the bug — that very public-key PEM as the
    HMAC secret for HS256. This is the classic RS256/HS256 confusion.
  * ``/`` mints a guest token (``role=guest``). ``/flag`` returns this instance's
    flag, but only to a token whose ``role`` is ``admin``.

Intended path: fetch the public key, forge ``{"role":"admin"}`` as an HS256 token
whose HMAC secret is the exact public-key PEM bytes, present it to ``/flag``.

The flag lives at ``/flag.txt`` (written by entrypoint.sh from the per-team
secret) and is served by no route other than the admin-gated ``/flag`` check —
there is no path that returns it without a valid admin token.
"""
import base64
import hashlib
import hmac
import json
import os

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from flask import Flask, jsonify, request

app = Flask(__name__)

# One RSA key pair per instance (per team). The public half is published; the
# private half signs guest tokens and never leaves the process.
_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PUB_PEM = _KEY.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64url_dec(txt: str) -> bytes:
    pad = "=" * (-len(txt) % 4)
    return base64.urlsafe_b64decode(txt + pad)


def _sign_rs256(signing_input: bytes) -> bytes:
    return _KEY.sign(signing_input, padding.PKCS1v15(), hashes_sha256())


def hashes_sha256():
    from cryptography.hazmat.primitives import hashes

    return hashes.SHA256()


def issue(role: str) -> str:
    header = {"alg": "RS256", "typ": "JWT"}
    payload = {"role": role, "iss": "jwt-relay"}
    signing_input = (
        _b64url(json.dumps(header).encode())
        + "."
        + _b64url(json.dumps(payload).encode())
    ).encode()
    sig = _sign_rs256(signing_input)
    return signing_input.decode() + "." + _b64url(sig)


def verify(token: str):
    """Return the token payload if the signature checks out, else None.

    Homegrown, and deliberately confused: ``key`` is the RSA public key, used
    directly as the HMAC secret when the header says HS256.
    """
    try:
        h_b64, p_b64, s_b64 = token.split(".")
    except ValueError:
        return None
    signing_input = (h_b64 + "." + p_b64).encode()
    try:
        header = json.loads(_b64url_dec(h_b64))
        payload = json.loads(_b64url_dec(p_b64))
        sig = _b64url_dec(s_b64)
    except Exception:
        return None

    alg = header.get("alg")
    key = _PUB_PEM  # the one and only "key" this verifier knows about
    if alg == "RS256":
        try:
            _KEY.public_key().verify(
                sig, signing_input, padding.PKCS1v15(), hashes_sha256()
            )
        except InvalidSignature:
            return None
        return payload
    if alg == "HS256":
        expected = hmac.new(key, signing_input, hashlib.sha256).digest()
        if hmac.compare_digest(expected, sig):
            return payload
        return None
    return None


@app.route("/")
def index():
    token = issue("guest")
    return jsonify(
        {
            "service": "jwt-relay",
            "hint": "verify your token offline with the published public key",
            "token": token,
            "endpoints": ["/pubkey", "/whoami", "/flag"],
        }
    )


@app.route("/pubkey")
def pubkey():
    return app.response_class(_PUB_PEM, mimetype="text/plain")


def _bearer():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer ") :].strip()
    return request.args.get("token", "")


@app.route("/whoami")
def whoami():
    payload = verify(_bearer())
    if payload is None:
        return jsonify({"error": "invalid or missing token"}), 401
    return jsonify({"role": payload.get("role")})


@app.route("/flag")
def flag():
    payload = verify(_bearer())
    if payload is None:
        return jsonify({"error": "invalid or missing token"}), 401
    if payload.get("role") != "admin":
        return jsonify({"error": "admin only"}), 403
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return jsonify({"flag": fh.read().strip()})
    except OSError:
        return jsonify({"error": "flag unavailable"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
