#!/usr/bin/env python3
"""Generate signal.txt: International Morse of the flag words."""

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

WORDS = ["MORSE", "CODE", "IS", "EASY"]
text = " / ".join(" ".join(MORSE[c] for c in w) for w in WORDS)
with open("../signal.txt", "w") as f:
    f.write(text + "\n")
