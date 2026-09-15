#!/usr/bin/env python3
"""Generate bits.txt: 8-bit binary ASCII of the flag."""

FLAG = "NCTF{binary_ones_and_zeros}"

bits = " ".join(format(b, "08b") for b in FLAG.encode())
with open("../bits.txt", "w") as f:
    f.write(bits + "\n")
