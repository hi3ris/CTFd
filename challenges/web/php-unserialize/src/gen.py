#!/usr/bin/env python3
"""Producer for php-unserialize artifacts (sealed hex + guest cookie)."""

import base64
import hashlib

SEED = "rot-2026-maintenance"
FLAG = "NCTF{php_object_injection_leaks_the_admin_secret}"


def main() -> None:
    ct = bytearray()
    data = FLAG.encode()
    for i, b in enumerate(data):
        ks = hashlib.md5(f"{SEED}:{i // 16}".encode()).digest()
        ct.append(b ^ ks[i % 16])
    print("sealed_hex =", ct.hex())
    ser = 'O:7:"Session":2:{s:3:"uid";i:42;s:4:"role";s:5:"guest";}'
    print("cookie =", base64.b64encode(ser.encode()).decode())


if __name__ == "__main__":
    main()
