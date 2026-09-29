#!/usr/bin/env python3
"""Predict the admin reset token from its logged timestamp and unseal the flag.

Offline. The token generator is a timestamp-seeded LCG (see app.py). The reset
log gives the exact second the admin token was issued; we confirm our LCG
reproduction against the logged guest tokens, then regenerate the admin token
and reproduce /reset/confirm.
"""

import datetime
import hashlib
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

A = 1664525
C = 1013904223
M = 2**32


def make_token(seed: int) -> str:
    state = seed % M
    parts = []
    for _ in range(4):
        state = (A * state + C) % M
        parts.append("%08x" % state)
    return "".join(parts)


def keystream(key: bytes, n: int) -> bytes:
    out = b""
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        counter += 1
    return out[:n]


def to_epoch(iso: str) -> int:
    dt = datetime.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ")
    return int(dt.replace(tzinfo=datetime.timezone.utc).timestamp())


def sealed_hex() -> str:
    src = open(os.path.join(ROOT, "app.py")).read()
    parts = re.findall(r'"([0-9a-f]+)"', src)
    return "".join(p for p in parts if p and all(c in "0123456789abcdef" for c in p))


def main() -> None:
    log = open(os.path.join(ROOT, "reset_log.txt")).read()

    # Verify the LCG reproduces every logged (timestamp -> token) pair.
    for iso, tok in re.findall(
        r"(\S+Z)\s+user=\w+\s+reset token issued: ([0-9a-f]{32})", log
    ):
        assert make_token(to_epoch(iso)) == tok, "LCG mismatch"

    admin_iso = re.search(r"(\S+Z)\s+user=admin", log).group(1)
    admin_token = make_token(to_epoch(admin_iso))

    key = hashlib.sha256(b"resetseal|" + admin_token.encode()).digest()
    ct = bytes.fromhex(sealed_hex())
    flag = bytes(a ^ b for a, b in zip(ct, keystream(key, len(ct)))).decode()
    print(flag)


if __name__ == "__main__":
    main()
