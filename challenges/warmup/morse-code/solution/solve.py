#!/usr/bin/env python3
"""Solver for morse-code: decode Morse and format the flag."""

import os

MORSE = {
    "A": ".-",
    "B": "-...",
    "C": "-.-.",
    "D": "-..",
    "E": ".",
    "F": "..-.",
    "G": "--.",
    "H": "....",
    "I": "..",
    "J": ".---",
    "K": "-.-",
    "L": ".-..",
    "M": "--",
    "N": "-.",
    "O": "---",
    "P": ".--.",
    "Q": "--.-",
    "R": ".-.",
    "S": "...",
    "T": "-",
    "U": "..-",
    "V": "...-",
    "W": ".--",
    "X": "-..-",
    "Y": "-.--",
    "Z": "--..",
}
INV = {v: k for k, v in MORSE.items()}

here = os.path.dirname(__file__)
text = open(os.path.join(here, "..", "signal.txt")).read().strip()
words = [w.strip() for w in text.split("/")]
decoded = ["".join(INV[c] for c in w.split()) for w in words]
print("NCTF{" + "_".join(w.lower() for w in decoded) + "}")
