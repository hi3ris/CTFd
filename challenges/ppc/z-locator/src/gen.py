#!/usr/bin/env python3
"""Generate data.txt for z-locator.

Line 1 is a distinctive pattern P. Lines 2.. are a large text T. The pattern
occurs exactly len(FLAG) times in T; the character immediately AFTER each
occurrence (in order of occurrence) spells the flag. Random filler makes naive
eyeballing hopeless; the intended tool is the Z-function (or KMP).
"""

import os
import random

FLAG = "NCTF{z_function_finds_every_needle_fast}"
PATTERN = "Qx7#zZ"  # distinctive, will not appear by chance in [a-z] filler
SEED = 4242
FILLER_ALPHABET = "abcdefghijklmnopqrstuvwxyz"


def filler(rng, n):
    return "".join(rng.choice(FILLER_ALPHABET) for _ in range(n))


def main():
    rng = random.Random(SEED)
    parts = []
    for ch in FLAG:
        parts.append(filler(rng, rng.randint(300, 900)))
        # Emit the pattern followed by the flag char (also lowercased letters
        # around keep the pattern boundary clean).
        parts.append(PATTERN)
        parts.append(ch)
    parts.append(filler(rng, rng.randint(300, 900)))
    text = "".join(parts)

    # Sanity: the pattern must occur exactly len(FLAG) times.
    assert text.count(PATTERN) == len(FLAG), text.count(PATTERN)

    out = os.path.join(os.path.dirname(__file__), "..", "data.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(PATTERN + "\n")
        fh.write(text + "\n")
    print("wrote", os.path.relpath(out), "text_len:", len(text))


if __name__ == "__main__":
    main()
