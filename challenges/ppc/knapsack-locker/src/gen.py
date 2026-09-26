#!/usr/bin/env python3
"""Generate items.txt for knapsack-locker.

A 0/1 knapsack instance (capacity + weight/value pairs). The optimal achievable
value is a large integer; its decimal string seeds a SHA-256 keystream that
XOR-encrypts the flag. Only the exact optimum decrypts it, so a wrong DP yields
garbage. The optimum is NOT stored; the player must compute it.
"""

import hashlib
import os
import random

FLAG = "NCTF{knapsack_optimum_unlocks_the_vault}"
SEED = 31337
N = 60
CAP = 2000


def knapsack(weights, values, cap):
    dp = [0] * (cap + 1)
    for w, v in zip(weights, values):
        for c in range(cap, w - 1, -1):
            if dp[c - w] + v > dp[c]:
                dp[c] = dp[c - w] + v
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
    rng = random.Random(SEED)
    weights = [rng.randint(20, 300) for _ in range(N)]
    values = [rng.randint(50, 1000) for _ in range(N)]

    best = knapsack(weights, values, CAP)
    ks = keystream(best, len(FLAG))
    cipher = bytes(a ^ b for a, b in zip(FLAG.encode(), ks))

    out = os.path.join(os.path.dirname(__file__), "..", "items.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(f"CAP {CAP}\n")
        fh.write(f"N {N}\n")
        for w, v in zip(weights, values):
            fh.write(f"{w} {v}\n")
        fh.write("CIPHER " + cipher.hex() + "\n")
    print("wrote", os.path.relpath(out), "optimum:", best)


if __name__ == "__main__":
    main()
