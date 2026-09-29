#!/usr/bin/env python3
"""
Static solver for 'byte-drift'.

The check applies an invertible per-byte transform to the input and compares
it to an embedded array target[]:

    enc[i] = ROL8( (p[i] + (i*3 + 7)) & 0xFF , (i % 7) + 1 ) ^ 0x5C

which inverts to:

    x     = enc[i] ^ 0x5C
    x     = ROR8(x, (i % 7) + 1)
    p[i]  = (x - (i*3 + 7)) & 0xFF

target[] lives in .rodata. We scan every window, invert it, and keep the one
that inverts to a clean NCTF{...} string. Nothing is hardcoded, so this survives
a rebuild with a different flag.

Usage: python3 solve.py [path-to-chall]
"""

import sys


def ror8(v, r):
    return ((v >> r) | (v << (8 - r))) & 0xFF


def invert(window):
    out = bytearray()
    for i, b in enumerate(window):
        x = ror8(b ^ 0x5C, (i % 7) + 1)
        out.append((x - (i * 3 + 7)) & 0xFF)
    return bytes(out)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "../chall"
    data = open(path, "rb").read()

    for off in range(len(data) - 5):
        # cheap anchor: does this window start decoding to "NCTF{"?
        if invert(data[off : off + 5]) != b"NCTF{":
            continue
        for end in range(off + 6, min(off + 96, len(data))):
            cand = invert(data[off : end + 1])
            if cand.endswith(b"}") and all(32 <= c < 127 for c in cand):
                print("flag:", cand.decode())
                return
    print("no solution found", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
