#!/usr/bin/env python3
"""Deterministic generator for the 'affine-relay' challenge.

Encrypts a short intercepted memo with a classic affine cipher over the
uppercase alphabet: letters map as E(x) = (a*x + b) mod 26, every non-letter
(spaces, punctuation, digits, and the flag's braces/underscores) passes through
untouched. The flag is embedded verbatim in the plaintext.
"""
import os

A = 5  # must be coprime with 26
B = 8

FLAG = "NCTF{affine_ciphers_are_just_linear_maps_mod_twenty_six}"

PLAINTEXT = (
    "AGENT REPORT FOLLOWS. THE COURIER SWAPPED EVERY LETTER USING A SIMPLE "
    "LINEAR RULE AND LEFT THE PUNCTUATION ALONE, SO THE SPACING SURVIVED THE "
    "RELAY INTACT. HEADQUARTERS INSISTS THE SCHEME IS UNBREAKABLE, YET THE "
    "KEYSPACE IS LAUGHABLY SMALL. THE EXTRACTION PHRASE FOR TONIGHT IS "
    f"{FLAG} AND IT MUST BE READ BACK EXACTLY. END OF TRANSMISSION."
)


def encrypt(text: str) -> str:
    out = []
    for ch in text:
        if "A" <= ch <= "Z":
            x = ord(ch) - ord("A")
            out.append(chr((A * x + B) % 26 + ord("A")))
        else:
            out.append(ch)
    return "".join(out)


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(here, "..", "cipher.txt")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(encrypt(PLAINTEXT) + "\n")
    print("wrote", os.path.normpath(out_path))


if __name__ == "__main__":
    main()
