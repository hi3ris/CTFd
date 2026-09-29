#!/usr/bin/env python3
"""Find every occurrence of the pattern with the Z-function and read the flag.

Build S = pattern + chr(1) + text and compute its Z-array. Positions i where
Z[i] == len(pattern) mark occurrences of the pattern inside text; the character
just past each match, in order, is a flag byte.
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data.txt")


def z_function(s):
    n = len(s)
    z = [0] * n
    lo = r = 0
    for i in range(1, n):
        if i < r:
            z[i] = min(r - i, z[i - lo])
        while i + z[i] < n and s[z[i]] == s[i + z[i]]:
            z[i] += 1
        if i + z[i] > r:
            lo, r = i, i + z[i]
    return z


def main():
    with open(DATA, encoding="utf-8") as fh:
        pattern = fh.readline().rstrip("\n")
        text = fh.readline().rstrip("\n")

    m = len(pattern)
    s = pattern + "\x01" + text
    z = z_function(s)
    base = m + 1  # index in s where text starts
    flag_chars = []
    for i in range(base, len(s)):
        if z[i] == m:
            end = (i - base) + m  # index in text just past the match
            if end < len(text):
                flag_chars.append(text[end])
    print("".join(flag_chars))


if __name__ == "__main__":
    main()
