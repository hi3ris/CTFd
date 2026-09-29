#!/usr/bin/env python3
"""Producer for the jwt-forge artifacts (SEALED_FLAG_HEX + guest token)."""

import hashlib

import jwt

SECRET = "c0nsole-rot4tion-signing-key-2026"
FLAG = "NCTF{hs256_forged_admin_and_unsealed_the_ops_flag}"


def keystream(key: bytes, n: int) -> bytes:
    out = b""
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        counter += 1
    return out[:n]


def main() -> None:
    key = hashlib.sha256(SECRET.encode() + b"|ops-seal").digest()
    ct = bytes(a ^ b for a, b in zip(FLAG.encode(), keystream(key, len(FLAG))))
    print("SEALED_FLAG_HEX =", ct.hex())
    print(
        "guest token     =",
        jwt.encode({"sub": "guest", "role": "guest"}, SECRET, algorithm="HS256"),
    )


if __name__ == "__main__":
    main()
