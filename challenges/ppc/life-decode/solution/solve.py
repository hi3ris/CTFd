#!/usr/bin/env python3
"""Run Conway's Game of Life for the given generations; decrypt the flag.

Header: W H GENERATIONS. Then CIPHER <hex>, then H rows of W bits (the initial
board). Boundary is dead (out-of-board neighbours count as 0). After stepping
GENERATIONS times, hash the flattened final board into a SHA-256 keystream and
XOR it against CIPHER.
"""

import hashlib
import os

HERE = os.path.dirname(os.path.abspath(__file__))
GRID = os.path.join(HERE, "..", "grid.txt")


def step(grid, w, h):
    nxt = [[0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            c = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w:
                        c += grid[ny][nx]
            if grid[y][x]:
                nxt[y][x] = 1 if c in (2, 3) else 0
            else:
                nxt[y][x] = 1 if c == 3 else 0
    return nxt


def keystream(seed_bytes, n):
    out = bytearray()
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(seed_bytes + counter.to_bytes(4, "big")).digest()
        counter += 1
    return bytes(out[:n])


def main():
    with open(GRID, encoding="utf-8") as fh:
        w, h, gens = map(int, fh.readline().split())
        cipher = bytes.fromhex(fh.readline().split()[1])
        grid = [[int(c) for c in fh.readline().strip()] for _ in range(h)]

    for _ in range(gens):
        grid = step(grid, w, h)

    bits = "".join(str(grid[y][x]) for y in range(h) for x in range(w)).encode()
    ks = keystream(bits, len(cipher))
    print(bytes(c ^ k for c, k in zip(cipher, ks)).decode())


if __name__ == "__main__":
    main()
