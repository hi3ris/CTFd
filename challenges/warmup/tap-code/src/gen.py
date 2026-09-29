#!/usr/bin/env python3
"""Generate taps.txt: Polybius/tap-code coords for the flag words."""

SQUARE = ["ABCDE", "FGHIJ", "LMNOP", "QRSTU", "VWXYZ"]
POS = {}
for r, row in enumerate(SQUARE, 1):
    for c, ch in enumerate(row, 1):
        POS[ch] = f"{r}{c}"

PLAIN = "TAP CODE POLYBIUS"
words = [" ".join(POS[c] for c in w) for w in PLAIN.split()]
with open("../taps.txt", "w") as f:
    f.write("  ".join(words) + "\n")
