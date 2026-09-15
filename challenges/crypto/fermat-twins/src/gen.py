#!/usr/bin/env python3
"""Deterministic generator for the 'fermat-twins' challenge.

Textbook RSA where the two primes are chosen very close together, so the modulus
falls to Fermat factorization. Produces a PEM public key and a hex ciphertext of
the flag.
"""
import os

from Crypto.PublicKey import RSA
from Crypto.Util.number import getPrime, isPrime

FLAG = b"NCTF{fermat_factoring_when_p_and_q_are_neighbours}"

E = 65537
SEED = 20260914  # deterministic prime selection


def next_prime(n: int) -> int:
    if n % 2 == 0:
        n += 1
    while not isPrime(n):
        n += 2
    return n


def main() -> None:
    import random

    random.seed(SEED)
    # A 512-bit prime, then a second prime only a small distance away.
    p = getPrime(512, randfunc=lambda k: random.getrandbits(k * 8).to_bytes(k, "big"))
    q = next_prime(p + random.getrandbits(40))
    n = p * q
    m = int.from_bytes(FLAG, "big")
    assert m < n
    c = pow(m, E, n)

    here = os.path.dirname(os.path.abspath(__file__))
    pub = RSA.construct((n, E)).export_key()
    with open(os.path.join(here, "..", "pubkey.pem"), "wb") as fh:
        fh.write(pub + b"\n")
    with open(os.path.join(here, "..", "ciphertext.txt"), "w", encoding="utf-8") as fh:
        fh.write(format(c, "x") + "\n")
    print("wrote pubkey.pem and ciphertext.txt; |p-q| =", abs(p - q))


if __name__ == "__main__":
    main()
