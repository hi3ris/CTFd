#!/usr/bin/env python3
"""Factor each semiprime, take the smaller prime mod 256, XOR-decrypt the flag.

Trial division up to sqrt(n) (bounded by 10^6 here) finds the smaller factor of
each n = p*q directly. The keystream byte for line i is (smaller prime) % 256.
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "semiprimes.txt")


def smaller_factor(n):
    d = 2
    while d * d <= n:
        if n % d == 0:
            return d
        d += 1 if d == 2 else 2
    return n  # prime (should not happen for a semiprime)


def main():
    cipher = None
    ks = []
    with open(DATA, encoding="utf-8") as fh:
        for line in fh:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "CIPHER":
                cipher = bytes.fromhex(parts[1])
            else:
                ks.append(smaller_factor(int(parts[0])) % 256)

    flag = bytes(c ^ k for c, k in zip(cipher, ks))
    print(flag.decode())


if __name__ == "__main__":
    main()
