#!/usr/bin/env python3
"""Producer for mass-assignment artifacts (users.json + sealed flag).

The flag is sealed with a key derived from the privileged mass-assignment body
(the canonical JSON of {"is_admin": true, "role": "admin"}), so only crafting
that exact request yields the key offline.
"""

import hashlib
import json

FLAG = "NCTF{mass_assignment_promoted_me_to_admin_role}"

# The privileged assignment a solver must craft; its canonical JSON is the key.
PRIVILEGED_ASSIGNMENT = {"is_admin": True, "role": "admin"}


def keystream(key: bytes, n: int) -> bytes:
    out = b""
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        counter += 1
    return out[:n]


def main() -> None:
    canonical = json.dumps(PRIVILEGED_ASSIGNMENT, sort_keys=True, separators=(",", ":"))
    key = hashlib.sha256(canonical.encode()).digest()
    ct = bytes(a ^ b for a, b in zip(FLAG.encode(), keystream(key, len(FLAG))))
    print("canonical assignment =", canonical)
    print("SEALED_FLAG_HEX =", ct.hex())
    store = {
        "users": [
            {
                "id": 7,
                "username": "kwame",
                "display": "Kwame",
                "email": "kwame@example.tg",
                "role": "member",
                "is_admin": False,
            }
        ]
    }
    print(json.dumps(store, indent=2))


if __name__ == "__main__":
    main()
