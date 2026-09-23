#!/usr/bin/env python3
"""Reference solver for crypto-sealbox-ecb (AES-ECB cut-and-paste).

Plaintext layout is ``name=<name>&role=user`` (16-byte ECB blocks). We (1) get a
block that decrypts to ``admin`` + PKCS#7 padding, (2) align a token so its last
block is exactly the role value, then splice -> ``role=admin``.

    python3 solve.py http://HOST:PORT
"""
import json
import sys
import urllib.parse
import urllib.request

BS = 16


def token(base, name_bytes):
    q = urllib.parse.urlencode({"name": name_bytes.decode("latin1")})
    url = base.rstrip("/") + "/token?" + q
    return bytes.fromhex(
        json.loads(urllib.request.urlopen(url, timeout=10).read())["token"]
    )


def solve(base):
    base = base.rstrip("/")
    # A: "name=" (5) + 11 filler => block0 full; then "admin"+11*pad => block1.
    ct_a = token(base, b"A" * 11 + b"admin" + bytes([11]) * 11)
    c_admin = ct_a[BS : 2 * BS]
    # B: name "AAAAA" => "name=AAAAA&role=" (block0) + "user"+pad (block1).
    ct_b = token(base, b"AAAAA")
    forged = (ct_b[:BS] + c_admin).hex()
    url = base + "/flag?token=" + forged
    return json.loads(urllib.request.urlopen(url, timeout=10).read())["flag"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
