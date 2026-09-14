"""Recover the flag from the zero-width characters in the shipped memo.

Keeps only U+200B / U+200C in reading order, maps them to bits (0/1), and packs
8 bits per byte.
"""

import os

ART = os.path.join(os.path.dirname(__file__), "..", "memo.txt")
ZERO = "​"
ONE = "‌"


def solve(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    bits = [c == ONE for c in text if c in (ZERO, ONE)]
    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        byte = 0
        for bit in bits[i : i + 8]:
            byte = (byte << 1) | int(bit)
        out.append(byte)
    return out.decode()


if __name__ == "__main__":
    print(solve(ART))
