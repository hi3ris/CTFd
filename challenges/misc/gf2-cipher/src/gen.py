#!/usr/bin/env python3
"""Emit system.json for gf2-cipher.

We encode the flag as a bit vector x (MSB-first per byte) and build an
invertible n x n matrix A over GF(2) as the product of a random unit
lower-triangular and unit upper-triangular matrix (guaranteed non-singular).
We ship A and b = A*x. Recovering x means solving the linear system over GF(2);
because A is invertible the solution is unique. The flag is never stored
directly.

Rows are stored as hex integers whose bit j is column j.
"""

import json
import os
import random

FLAG = b"NCTF{linear_over_gf2_is_gaussian}"


def flag_bits() -> int:
    x = 0
    for j, byte in enumerate(FLAG):
        for k in range(8):
            bit = (byte >> (7 - k)) & 1
            if bit:
                x |= 1 << (8 * j + k)
    return x


def main() -> None:
    rng = random.Random(0xC0FFEE)
    n = 8 * len(FLAG)

    # Unit lower- and upper-triangular random matrices (rows as ints).
    lower = []
    upper = []
    for i in range(n):
        low = 1 << i
        for j in range(i):
            if rng.getrandbits(1):
                low |= 1 << j
        lower.append(low)
        up = 1 << i
        for j in range(i + 1, n):
            if rng.getrandbits(1):
                up |= 1 << j
        upper.append(up)

    # A = lower * upper over GF(2). Row i = XOR of upper[k] for set bits k in lower[i].
    a_rows = []
    for i in range(n):
        row = 0
        li = lower[i]
        k = 0
        while li:
            if li & 1:
                row ^= upper[k]
            li >>= 1
            k += 1
        a_rows.append(row)

    x = flag_bits()
    b = [bin(row & x).count("1") & 1 for row in a_rows]

    data = {
        "n": n,
        "note": "solve A x = b over GF(2); row bit j is column j; x is the flag bits (MSB-first per byte)",
        "A": [format(row, "x") for row in a_rows],
        "b": "".join(str(v) for v in b),
    }
    out = os.path.join(os.path.dirname(__file__), "..", "system.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    print("wrote", os.path.relpath(out), "n:", n)


if __name__ == "__main__":
    main()
