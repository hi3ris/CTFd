#!/usr/bin/env python3
"""Reference solver for crypto-nonce-climb.

Chain: request two signatures for different (non-admin) messages -> they share
the reused nonce (same r) -> recover k, then the private key d -> sign the admin
command ourselves -> present it to /flag.

    python3 solve.py http://HOST:PORT
"""
import hashlib
import json
import sys
import urllib.parse
import urllib.request

N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
G = (GX, GY)


def inv(x, m):
    return pow(x, -1, m)


def ec_add(a, b):
    if a is None:
        return b
    if b is None:
        return a
    x1, y1 = a
    x2, y2 = b
    if x1 == x2 and (y1 + y2) % P == 0:
        return None
    if a == b:
        m = (3 * x1 * x1) * inv(2 * y1, P) % P
    else:
        m = (y2 - y1) * inv((x2 - x1) % P, P) % P
    x3 = (m * m - x1 - x2) % P
    return (x3, (m * (x1 - x3) - y1) % P)


def ec_mul(k, pt):
    r = None
    while k:
        if k & 1:
            r = ec_add(r, pt)
        pt = ec_add(pt, pt)
        k >>= 1
    return r


def z(msg):
    return int.from_bytes(hashlib.sha256(msg.encode()).digest(), "big") % N


def get(base, path, **params):
    url = base + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return json.loads(urllib.request.urlopen(url, timeout=10).read().decode())


def solve(base):
    base = base.rstrip("/")
    admin = get(base, "/")["admin_command"]

    s1 = get(base, "/sign", msg="alpha")
    s2 = get(base, "/sign", msg="bravo")
    r = int(s1["r"], 16)
    assert r == int(s2["r"], 16), "nonce not reused (r differs)"
    z1, z2 = z("alpha"), z("bravo")
    sig1, sig2 = int(s1["s"], 16), int(s2["s"], 16)

    # same k: k = (z1 - z2) / (s1 - s2);  d = (s*k - z) / r
    k = ((z1 - z2) * inv((sig1 - sig2) % N, N)) % N
    d = ((sig1 * k - z1) * inv(r, N)) % N

    # forge a signature for the admin command with the recovered key (fresh k)
    kf = 0x1234567890ABCDEF1234567890ABCDEF
    za = z(admin)
    rf = ec_mul(kf, G)[0] % N
    sf = (inv(kf, N) * (za + rf * d)) % N

    out = get(base, "/flag", msg=admin, r=hex(rf), s=hex(sf))
    return out["flag"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
