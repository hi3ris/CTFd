#!/usr/bin/env python3
"""Generate grid.txt for life-decode.

A random initial state for Conway's Game of Life on a fixed W x H board with
DEAD boundaries (cells outside the board count as dead). We evolve GENERATIONS
steps, hash the final board, and use that as a SHA-256 keystream to XOR-encrypt
the flag. Only the correct rule + boundary + step count reproduces the final
state and decrypts the flag.
"""

import hashlib
import os
import random

FLAG = "NCTF{conway_life_evolves_to_this_state}"
SEED = 90210
W, H = 64, 48
GENERATIONS = 120
DENSITY = 0.30


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


def to_bytes(grid, w, h):
    bits = "".join(str(grid[y][x]) for y in range(h) for x in range(w))
    return bits.encode()


def keystream(seed_bytes, n):
    out = bytearray()
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(seed_bytes + counter.to_bytes(4, "big")).digest()
        counter += 1
    return bytes(out[:n])


def main():
    rng = random.Random(SEED)
    grid = [[1 if rng.random() < DENSITY else 0 for _ in range(W)] for _ in range(H)]
    initial = [row[:] for row in grid]

    for _ in range(GENERATIONS):
        grid = step(grid, W, H)

    ks = keystream(to_bytes(grid, W, H), len(FLAG))
    cipher = bytes(ord(c) ^ k for c, k in zip(FLAG, ks))

    out = os.path.join(os.path.dirname(__file__), "..", "grid.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(f"{W} {H} {GENERATIONS}\n")
        fh.write("CIPHER " + cipher.hex() + "\n")
        for row in initial:
            fh.write("".join(str(c) for c in row) + "\n")
    print("wrote", os.path.relpath(out))


if __name__ == "__main__":
    main()
