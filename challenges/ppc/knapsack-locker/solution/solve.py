#!/usr/bin/env python3
"""Solve the 0/1 knapsack, then use the optimum to derive the XOR keystream.

The optimal value V comes from the standard 1-D DP. keystream = SHA-256 blocks
of the decimal string of V (with a block counter); XOR it against CIPHER to
recover the flag.
"""

import hashlib
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(HERE, "..", "items.txt")


def knapsack(weights, values, cap):
    dp = [0] * (cap + 1)
    for w, v in zip(weights, values):
        for c in range(cap, w - 1, -1):
            cand = dp[c - w] + v
            if cand > dp[c]:
                dp[c] = cand
    return dp[cap]


def keystream(seed_int, n):
    out = bytearray()
    counter = 0
    material = str(seed_int).encode()
    while len(out) < n:
        out += hashlib.sha256(material + counter.to_bytes(4, "big")).digest()
        counter += 1
    return bytes(out[:n])


def main():
    cap = None
    weights, values = [], []
    cipher = None
    with open(ITEMS, encoding="utf-8") as fh:
        for line in fh:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "CAP":
                cap = int(parts[1])
            elif parts[0] == "N":
                continue
            elif parts[0] == "CIPHER":
                cipher = bytes.fromhex(parts[1])
            else:
                weights.append(int(parts[0]))
                values.append(int(parts[1]))

    best = knapsack(weights, values, cap)
    ks = keystream(best, len(cipher))
    flag = bytes(a ^ b for a, b in zip(cipher, ks))
    print(flag.decode())


if __name__ == "__main__":
    main()
