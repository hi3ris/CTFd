#!/usr/bin/env python3
"""
Static solver for 'keygen-me'.

The validator enforces a chained constraint system on the 48 base32 symbols
v[0..47] of the license key:

    v[0]                              == t[0]
    (v[i] + 3*v[i-1] + 7*i + 0x1B) % 32 == t[i]   (i >= 1)

This is triangular, so it has a unique solution by forward substitution:

    v[0] = t[0]
    v[i] = (t[i] - 3*v[i-1] - 7*i - 0x1B) % 32

The solved v[] IS the base32 encoding of the flag, so repacking the 5-bit groups
into bytes gives NCTF{...}. The target array t[] is 48 bytes (each < 32) in the
binary; we slide over the file, solve, repack, and keep the window that yields a
clean NCTF{...}. Nothing is hardcoded.

Usage: python3 solve.py [path-to-chall]
"""

import sys

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
N = 48


def solve_chain(t):
    v = [t[0] % 32]
    for i in range(1, N):
        v.append((t[i] - 3 * v[i - 1] - 7 * i - 0x1B) % 32)
    return v


def repack(v):
    bits = "".join("{:05b}".format(x) for x in v)
    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        out.append(int(bits[i : i + 8], 2))
    return bytes(out)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "../chall"
    data = open(path, "rb").read()

    for off in range(len(data) - N):
        window = data[off : off + N]
        if any(b >= 32 for b in window):
            continue
        v = solve_chain(list(window))
        flag = repack(v)
        if flag.startswith(b"NCTF{") and flag.endswith(b"}") and flag.isascii():
            serial = "".join(ALPHABET[x] for x in v)
            grouped = "-".join(serial[i : i + 8] for i in range(0, len(serial), 8))
            print("serial:", grouped)
            print("flag  :", flag.decode())
            return
    print("no solution found", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
