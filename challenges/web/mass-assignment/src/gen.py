#!/usr/bin/env python3
"""Producer for mass-assignment artifacts (users.json + sealed flag)."""

import hashlib
import json

FLAG = "NCTF{mass_assignment_promoted_me_to_admin_role}"
ADMIN_SEAL_KEY = b"profile-svc-admin-seal-2026"


def keystream(key: bytes, n: int) -> bytes:
    out = b""
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        counter += 1
    return out[:n]


def main() -> None:
    ct = bytes(
        a ^ b
        for a, b in zip(
            FLAG.encode(), keystream(hashlib.sha256(ADMIN_SEAL_KEY).digest(), len(FLAG))
        )
    )
    print("SEALED_FLAG_HEX =", ct.hex())
    store = {
        "users": [
            {
                "id": 7,
                "username": "kwame",
                "display": "Kwame",
                "email": "kwame@example.tg",
                "is_admin": False,
            }
        ]
    }
    print(json.dumps(store, indent=2))


if __name__ == "__main__":
    main()
