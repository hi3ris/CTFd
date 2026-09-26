#!/usr/bin/env python3
"""Deterministic generator for the 'modulus-siblings' challenge.

The same flag is encrypted twice under the same RSA modulus with two different,
coprime public exponents. Ships a JSON transcript with n, the two exponents, and
the two ciphertexts (all hex).
"""
import json
import os
import random

from Crypto.Util.number import getPrime

FLAG = b"NCTF{one_message_two_coprime_exponents_shared_modulus}"

E1 = 65537
E2 = 257


def main() -> None:
    random.seed(4242)
    rf = lambda k: random.getrandbits(k * 8).to_bytes(k, "big")  # noqa: E731
    p = getPrime(512, randfunc=rf)
    q = getPrime(512, randfunc=rf)
    n = p * q
    m = int.from_bytes(FLAG, "big")
    assert m < n
    c1 = pow(m, E1, n)
    c2 = pow(m, E2, n)

    transcript = {
        "n": format(n, "x"),
        "e1": E1,
        "e2": E2,
        "c1": format(c1, "x"),
        "c2": format(c2, "x"),
    }
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "..", "transcript.json"), "w", encoding="utf-8") as fh:
        json.dump(transcript, fh, indent=2)
        fh.write("\n")
    print("wrote transcript.json")


if __name__ == "__main__":
    main()
