#!/usr/bin/env python3
"""OIDC Forge — a resource server that trusts ``alg=none`` ID tokens.

Design (served challenge, per-team flag):

  * ``/token`` mints a normal OIDC-style ID token for a guest (signed HS256 with a
    per-instance secret you never see).
  * ``/admin/flag`` validates the presented ID token and returns this instance's
    flag when the token's ``groups`` contains ``platform-admin``.
  * The misconfiguration: the validator honours the token header's ``alg``. When
    ``alg`` is ``none`` it treats the token as **unsigned and accepts it without
    any signature check** — the classic "alg:none" OIDC/JWT flaw.

Intended path: forge an unsigned ID token
``{"alg":"none"}`` / ``{"sub":"you","groups":["platform-admin"]}`` and present it
to ``/admin/flag``. No secret needed — the server skips verification for alg=none.

The flag at ``/flag.txt`` is exposed by no route other than this group check.
"""
import base64
import hashlib
import hmac
import json
import os

from flask import Flask, jsonify, request

app = Flask(__name__)

_SECRET = os.urandom(32)  # HS256 signing secret, per instance, never exposed


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def b64url_dec(txt: str) -> bytes:
    return base64.urlsafe_b64decode(txt + "=" * (-len(txt) % 4))


def issue(claims: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    si = (
        b64url(json.dumps(header).encode()) + "." + b64url(json.dumps(claims).encode())
    ).encode()
    sig = hmac.new(_SECRET, si, hashlib.sha256).digest()
    return si.decode() + "." + b64url(sig)


def validate(token: str):
    parts = token.split(".")
    if len(parts) not in (2, 3):
        return None
    try:
        header = json.loads(b64url_dec(parts[0]))
        claims = json.loads(b64url_dec(parts[1]))
    except Exception:
        return None
    alg = (header.get("alg") or "").lower()
    if alg == "none":
        # Misconfig: unsigned tokens are accepted as-is.
        return claims
    if alg == "hs256" and len(parts) == 3:
        si = (parts[0] + "." + parts[1]).encode()
        expected = hmac.new(_SECRET, si, hashlib.sha256).digest()
        if hmac.compare_digest(expected, b64url_dec(parts[2])):
            return claims
    return None


@app.route("/")
def index():
    return jsonify(
        {
            "service": "cdn-oidc",
            "token": "/token -> guest id_token",
            "admin": "/admin/flag  (Authorization: Bearer <id_token>)",
            "need": "groups contains 'platform-admin'",
        }
    )


@app.route("/token")
def token():
    return jsonify({"id_token": issue({"sub": "guest", "groups": ["users"]})})


def _bearer():
    auth = request.headers.get("Authorization", "")
    return (
        auth[7:].strip()
        if auth.startswith("Bearer ")
        else request.args.get("token", "")
    )


@app.route("/admin/flag")
def admin_flag():
    claims = validate(_bearer())
    if claims is None:
        return jsonify({"error": "invalid token"}), 401
    if "platform-admin" not in (claims.get("groups") or []):
        return jsonify({"error": "not a platform admin"}), 403
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return jsonify({"flag": fh.read().strip()})
    except OSError:
        return jsonify({"error": "flag unavailable"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
