#!/usr/bin/env python3
"""Solver for tap-code: map (row,col) -> letter, then format."""

import os

SQUARE = ["ABCDE", "FGHIJ", "LMNOP", "QRSTU", "VWXYZ"]

here = os.path.dirname(__file__)
text = open(os.path.join(here, "..", "taps.txt")).read().strip()
words = []
for group in text.split("  "):
    letters = []
    for code in group.split():
        r, c = int(code[0]) - 1, int(code[1]) - 1
        letters.append(SQUARE[r][c])
    words.append("".join(letters))
print("NCTF{" + "_".join(w.lower() for w in words) + "}")
