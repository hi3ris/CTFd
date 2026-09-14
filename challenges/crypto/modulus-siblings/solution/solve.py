#!/usr/bin/env python3
"""Reference solver for 'modulus-siblings'.

Same message m under one modulus n with two coprime exponents e1, e2 and
ciphertexts c1 = m^e1, c2 = m^e2. Since gcd(e1, e2) = 1, the extended Euclidean
algorithm gives integers a, b with a*e1 + b*e2 = 1, hence

    c1^a * c2^b = m^(a*e1 + b*e2) = m   (mod n)

Negative exponents are handled with modular inverses.
"""
import json
import os
import sys


def egcd(a, b):
    if b == 0:
        return a, 1, 0
    g, x, y = egcd(b, a % b)
    return g, y, x - (a // b) * y


def solve(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        t = json.load(fh)
    n = int(t["n"], 16)
    e1, e2 = t["e1"], t["e2"]
    c1 = int(t["c1"], 16)
    c2 = int(t["c2"], 16)

    g, a, b = egcd(e1, e2)
    assert g == 1, "exponents are not coprime"

    if a < 0:
        c1 = pow(c1, -1, n)
        a = -a
    if b < 0:
        c2 = pow(c2, -1, n)
        b = -b

    m = pow(c1, a, n) * pow(c2, b, n) % n
    flag = m.to_bytes((m.bit_length() + 7) // 8, "big").decode()
    print("[+] FLAG =", flag)
    return flag


if __name__ == "__main__":
    default = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "transcript.json"
    )
    solve(sys.argv[1] if len(sys.argv) > 1 else default)
