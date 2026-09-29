#!/usr/bin/env python3
"""Solver for vigenere-known-key: decrypt with key WARMUP."""

import os


def vig_decrypt(ct, key):
    out = []
    ki = 0
    for c in ct:
        if "a" <= c <= "z":
            k = ord(key[ki % len(key)].lower()) - 97
            out.append(chr((ord(c) - 97 - k) % 26 + 97))
            ki += 1
        elif "A" <= c <= "Z":
            k = ord(key[ki % len(key)].lower()) - 97
            out.append(chr((ord(c) - 65 - k) % 26 + 65))
            ki += 1
        else:
            out.append(c)
    return "".join(out)


here = os.path.dirname(__file__)
ct = open(os.path.join(here, "..", "cipher.txt")).read().strip()
print(vig_decrypt(ct, "WARMUP"))
