#!/usr/bin/env python3
"""Deterministic generator for the 'twister-tell' challenge.

A token service leaks 624 consecutive 32-bit outputs of its Mersenne Twister
(MT19937) PRNG, then uses the *next* outputs of the very same stream as a
keystream to encrypt the flag. Ships the 624 leaked outputs and the ciphertext.
"""
import os
import random

FLAG = b"NCTF{mt19937_untempered_then_the_future_is_yours}"

SEED = 0xC0FFEE


def keystream_bytes(rng: random.Random, n: int) -> bytes:
    out = bytearray()
    while len(out) < n:
        out += rng.getrandbits(32).to_bytes(4, "big")
    return bytes(out[:n])


def main() -> None:
    rng = random.Random(SEED)
    leaked = [rng.getrandbits(32) for _ in range(624)]
    ks = keystream_bytes(rng, len(FLAG))
    ct = bytes(a ^ b for a, b in zip(FLAG, ks))

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "..", "outputs.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(str(x) for x in leaked) + "\n")
    with open(os.path.join(here, "..", "flag.enc"), "w", encoding="utf-8") as fh:
        fh.write(ct.hex() + "\n")
    print("wrote outputs.txt (624 samples) and flag.enc")


if __name__ == "__main__":
    main()
