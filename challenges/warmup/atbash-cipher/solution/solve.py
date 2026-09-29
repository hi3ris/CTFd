#!/usr/bin/env python3
"""Solver for atbash-cipher: mirror the alphabet (self-inverse)."""

import os


def atbash(s):
    out = []
    for c in s:
        if "a" <= c <= "z":
            out.append(chr(ord("z") - (ord(c) - ord("a"))))
        elif "A" <= c <= "Z":
            out.append(chr(ord("Z") - (ord(c) - ord("A"))))
        else:
            out.append(c)
    return "".join(out)


here = os.path.dirname(__file__)
data = open(os.path.join(here, "..", "secret.txt")).read().strip()
print(atbash(data))
