#!/usr/bin/env python3
"""Producer for ssti-jinja sealed flag blob."""

import hashlib

FLAG = "NCTF{jinja2_ssti_config_leak_via_render_string}"
VAULT_KEY = b"greeting-vault-2026"


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
            FLAG.encode(), keystream(hashlib.sha256(VAULT_KEY).digest(), len(FLAG))
        )
    )
    print("SEALED =", ct.hex())


if __name__ == "__main__":
    main()
