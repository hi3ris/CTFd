#!/usr/bin/env python3
"""Solve each congruence a*x = b (mod m) for x, then decrypt the flag.

Each modulus is prime and gcd(a, m) = 1, so x = b * a^(-1) mod m is unique.
Concatenate all solutions (comma-joined decimal), SHA-256 into a keystream, and
XOR against CIPHER.
"""

import hashlib
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SYSTEM = os.path.join(HERE, "..", "system.txt")


def main():
    cipher = None
    solutions = []
    with open(SYSTEM, encoding="utf-8") as fh:
        for line in fh:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "CIPHER":
                cipher = bytes.fromhex(parts[1])
            else:
                a, b, m = (int(v) for v in parts)
                x = (b * pow(a, -1, m)) % m
                solutions.append(x)

    material = ",".join(str(s) for s in solutions).encode()
    ks = hashlib.sha256(material).digest()
    while len(ks) < len(cipher):
        ks += hashlib.sha256(ks).digest()
    print(bytes(c ^ k for c, k in zip(cipher, ks)).decode())


if __name__ == "__main__":
    main()
