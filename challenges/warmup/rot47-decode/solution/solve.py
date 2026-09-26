#!/usr/bin/env python3
"""Solver for rot47-decode: ROT47 is its own inverse."""

import os


def rot47(s):
    out = []
    for c in s:
        o = ord(c)
        if 33 <= o <= 126:
            out.append(chr(33 + (o - 33 + 47) % 94))
        else:
            out.append(c)
    return "".join(out)


here = os.path.dirname(__file__)
data = open(os.path.join(here, "..", "secret.txt")).read().strip()
print(rot47(data))
