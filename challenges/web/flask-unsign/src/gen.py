#!/usr/bin/env python3
"""Producer for flask-unsign artifacts (guest cookie + sealed flag)."""

import hashlib

from flask import Flask
from flask.sessions import SecureCookieSessionInterface

SECRET = "s3cr3t-flask-signing-key-do-not-share-8842"
FLAG = "NCTF{itsdangerous_secret_key_resign_admin_session}"


def keystream(key: bytes, n: int) -> bytes:
    out = b""
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        counter += 1
    return out[:n]


def main() -> None:
    app = Flask(__name__)
    app.secret_key = SECRET
    s = SecureCookieSessionInterface().get_signing_serializer(app)
    print("cookie =", s.dumps({"uid": 7, "role": "guest", "display": "guest"}))
    key = hashlib.sha256(SECRET.encode() + b"|panel-seal").digest()
    ct = bytes(a ^ b for a, b in zip(FLAG.encode(), keystream(key, len(FLAG))))
    print("SEALED_FLAG_HEX =", ct.hex())


if __name__ == "__main__":
    main()
