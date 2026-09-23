#!/usr/bin/env python3
"""Reference solver for crypto-sign-slip.

The token "signature" is a keyless CRC32 of the role, so forge an admin token.

    python3 solve.py http://HOST:PORT
"""
import json
import sys
import urllib.request
from zlib import crc32


def _get(url, token=None):
    headers = {"X-Token": token} if token else {}
    req = urllib.request.Request(url, headers=headers)
    return json.loads(urllib.request.urlopen(req, timeout=10).read())


def solve(base):
    base = base.rstrip("/")
    role = "admin"
    sig = format(crc32(role.encode()) & 0xFFFFFFFF, "08x")
    token = f"role={role};sig={sig}"
    return _get(base + "/admin/flag", token)["flag"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
