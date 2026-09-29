#!/usr/bin/env python3
"""Solve A x = b over GF(2) by Gaussian elimination; rebuild the flag."""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
JSON = os.path.join(HERE, "..", "system.json")


def main() -> None:
    with open(JSON, encoding="utf-8") as fh:
        data = json.load(fh)

    n = data["n"]
    # Augment each row with its b bit stored in column n.
    rows = []
    for hex_row, bit in zip(data["A"], data["b"]):
        row = int(hex_row, 16)
        if bit == "1":
            row |= 1 << n
        rows.append(row)

    # Forward elimination: get a pivot in each column.
    pivot_for = {}
    for col in range(n):
        pivot = None
        for r in range(len(rows)):
            if r in pivot_for.values():
                continue
            if rows[r] >> col & 1:
                pivot = r
                break
        if pivot is None:
            raise SystemExit(f"no pivot for column {col}; matrix not full rank")
        pivot_for[col] = pivot
        for r in range(len(rows)):
            if r != pivot and (rows[r] >> col & 1):
                rows[r] ^= rows[pivot]

    # Read solution bit per column from its pivot row's augmented bit.
    x = 0
    for col in range(n):
        if rows[pivot_for[col]] >> n & 1:
            x |= 1 << col

    out = bytearray()
    for j in range(n // 8):
        byte = 0
        for k in range(8):
            byte = (byte << 1) | (x >> (8 * j + k) & 1)
        out.append(byte)
    print(out.decode())


if __name__ == "__main__":
    main()
