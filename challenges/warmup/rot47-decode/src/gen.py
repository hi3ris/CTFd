#!/usr/bin/env python3
"""Generate secret.txt: ROT47 of the flag."""


def rot47(s):
    out = []
    for c in s:
        o = ord(c)
        if 33 <= o <= 126:
            out.append(chr(33 + (o - 33 + 47) % 94))
        else:
            out.append(c)
    return "".join(out)


FLAG = "NCTF{rot47_shifts_the_glyphs}"
with open("../secret.txt", "w") as f:
    f.write(rot47(FLAG) + "\n")
