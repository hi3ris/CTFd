#!/usr/bin/env python3
"""Generate system.txt for congruence-vault.

We ship COUNT linear congruences a*x = b (mod m) with m prime and 1 <= a < m,
each having a unique solution x in [0, m). The concatenation of ALL solutions
(as decimal, comma-joined) is SHA-256'd into a keystream that XOR-encrypts the
flag, so every single congruence must be solved correctly.
"""

import hashlib
import os
import random

FLAG = "NCTF{modular_inverse_batch_solved_clean}"
SEED = 13579
COUNT = 160


def is_prime(n):
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def rand_prime(rng, lo, hi):
    while True:
        n = rng.randrange(lo, hi) | 1
        if is_prime(n):
            return n


def main():
    rng = random.Random(SEED)
    rows = []
    solutions = []
    for _ in range(COUNT):
        m = rand_prime(rng, 10**8, 10**9)
        a = rng.randrange(1, m)
        x = rng.randrange(0, m)  # the intended unique solution
        b = (a * x) % m
        rows.append((a, b, m))
        solutions.append(x)

    material = ",".join(str(s) for s in solutions).encode()
    ks = hashlib.sha256(material).digest()
    while len(ks) < len(FLAG):
        ks += hashlib.sha256(ks).digest()
    cipher = bytes(ord(c) ^ k for c, k in zip(FLAG, ks))

    out = os.path.join(os.path.dirname(__file__), "..", "system.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("CIPHER " + cipher.hex() + "\n")
        for a, b, m in rows:
            fh.write(f"{a} {b} {m}\n")
    print("wrote", os.path.relpath(out), "congruences:", len(rows))


if __name__ == "__main__":
    main()
