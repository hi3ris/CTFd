#!/usr/bin/env python3
"""Reference solver for 'fermat-twins'.

The RSA modulus is a product of two primes that are extremely close together.
Fermat's method writes n = a^2 - b^2 = (a - b)(a + b) and finds a, b quickly
when |p - q| is small: start a at ceil(sqrt(n)) and increment until a^2 - n is a
perfect square.
"""
import os
import sys
from math import isqrt

from Crypto.PublicKey import RSA


def fermat_factor(n: int):
    a = isqrt(n)
    if a * a < n:
        a += 1
    while True:
        b2 = a * a - n
        b = isqrt(b2)
        if b * b == b2:
            return a - b, a + b
        a += 1


def solve(pem_path: str, ct_path: str) -> str:
    with open(pem_path, "rb") as fh:
        key = RSA.import_key(fh.read())
    n, e = key.n, key.e
    with open(ct_path, encoding="utf-8") as fh:
        c = int(fh.read().strip(), 16)

    p, q = fermat_factor(n)
    assert p * q == n
    phi = (p - 1) * (q - 1)
    d = pow(e, -1, phi)
    m = pow(c, d, n)
    flag = m.to_bytes((m.bit_length() + 7) // 8, "big").decode()
    print(f"[+] |p-q| = {abs(p - q)}")
    print("[+] FLAG =", flag)
    return flag


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    pem = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "pubkey.pem")
    ct = (
        sys.argv[2] if len(sys.argv) > 2 else os.path.join(here, "..", "ciphertext.txt")
    )
    solve(pem, ct)
