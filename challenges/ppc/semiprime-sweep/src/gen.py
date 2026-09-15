#!/usr/bin/env python3
"""Generate semiprimes.txt for semiprime-sweep.

Each line is a semiprime n = p*q with distinct primes p < q drawn from
[10^4, 10^6], so n is up to ~10^12 and factorable by trial division to 10^6.
The smaller prime p of each, taken mod 256, forms a keystream that XOR-encrypts
the flag. Wrong factors -> wrong keystream -> garbage.
"""

import os
import random

FLAG = "NCTF{trial_division_splits_each_semiprime}"
SEED = 2718281


def sieve(limit):
    is_p = bytearray([1]) * (limit + 1)
    is_p[0] = is_p[1] = 0
    for i in range(2, int(limit**0.5) + 1):
        if is_p[i]:
            is_p[i * i :: i] = bytearray(len(is_p[i * i :: i]))
    return [i for i in range(limit + 1) if is_p[i]]


def main():
    rng = random.Random(SEED)
    primes = [p for p in sieve(1_000_000) if p >= 10_000]

    semis = []
    ks = []
    for _ch in FLAG:
        p = rng.choice(primes)
        q = rng.choice(primes)
        while q == p:
            q = rng.choice(primes)
        lo = min(p, q)
        semis.append(lo * max(p, q))
        ks.append(lo % 256)

    cipher = bytes(ord(c) ^ k for c, k in zip(FLAG, ks))

    out = os.path.join(os.path.dirname(__file__), "..", "semiprimes.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("CIPHER " + cipher.hex() + "\n")
        for n in semis:
            fh.write(f"{n}\n")
    print("wrote", os.path.relpath(out), "count:", len(semis))


if __name__ == "__main__":
    main()
