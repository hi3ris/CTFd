#!/usr/bin/env python3
"""Forge an admin HS256 token with the leaked secret, then unseal the flag.

Everything is offline: the secret is in config.env, the sealed flag is in
app.py. We rebuild the /api/flag admin path locally.
"""

import hashlib
import os
import re

import jwt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def leaked_secret() -> str:
    env = open(os.path.join(ROOT, "config.env")).read()
    return re.search(r"JWT_SECRET=(\S+)", env).group(1)


def sealed_hex() -> str:
    src = open(os.path.join(ROOT, "app.py")).read()
    parts = re.findall(r'"([0-9a-f]+)"', src)
    return "".join(p for p in parts if all(c in "0123456789abcdef" for c in p))


def keystream(key: bytes, n: int) -> bytes:
    out = b""
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        counter += 1
    return out[:n]


def main() -> None:
    secret = leaked_secret()

    # 1) forge an admin token exactly as the server would verify it
    forged = jwt.encode({"sub": "attacker", "role": "admin"}, secret, algorithm="HS256")
    claims = jwt.decode(forged, secret, algorithms=["HS256"])
    assert claims["role"] == "admin", "forgery failed"

    # 2) admin path unseals the flag with a keystream derived from the secret
    ct = bytes.fromhex(sealed_hex())
    key = hashlib.sha256(secret.encode() + b"|ops-seal").digest()
    flag = bytes(a ^ b for a, b in zip(ct, keystream(key, len(ct)))).decode()
    print(flag)


if __name__ == "__main__":
    main()
