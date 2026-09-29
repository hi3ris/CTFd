#!/usr/bin/env python3
"""Deterministic generator for the 'vigenere-drift' challenge.

A Vigenere variant with a twist: on top of the repeating base key, every full
period the effective shift *drifts* upward by one. For the n-th enciphered
letter (counting letters only), with base key K of length L:

    col   = n % L
    block = n // L
    shift = (K[col] + block) mod 26

Letters are enciphered (case preserved); all other characters pass through and
do not advance the letter counter. The flag is embedded in the plaintext.
"""
import os

BASE_KEY = "drift"  # -> shifts [3, 17, 8, 5, 19]

FLAG = "NCTF{progressive_key_drift_still_falls_to_chi_squared}"

PLAINTEXT = (
    "The archivist warned that no cipher survives contact with a patient "
    "reader, and this intercept is no exception. It masquerades as a simple "
    "repeating key scheme, yet the substitution alphabet quietly advances a "
    "little further with every full turn of the key, so identical plaintext "
    "letters rarely encrypt to the same symbol twice. The clerks believed this "
    "drift would defeat any statistical attack, but the underlying language is "
    "still ordinary English and the drift is perfectly regular, which means the "
    "structure can be peeled away one column at a time. Buried in the middle of "
    "this dull memorandum is the recovery token the analysts were sent to find, "
    "written as " + FLAG + " and repeated nowhere else in the document. The "
    "remainder of the note is deliberate filler, padding the message so that "
    "every column of the key is exercised many times over and letter frequency "
    "analysis has more than enough material to work with in each position."
)


def encrypt(text: str, key: str) -> str:
    shifts = [ord(c) - ord("a") for c in key.lower()]
    length = len(shifts)
    out = []
    n = 0
    for ch in text:
        if "a" <= ch <= "z" or "A" <= ch <= "Z":
            base = ord("a") if ch.islower() else ord("A")
            x = ord(ch) - base
            s = (shifts[n % length] + n // length) % 26
            out.append(chr((x + s) % 26 + base))
            n += 1
        else:
            out.append(ch)
    return "".join(out)


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(here, "..", "cipher.txt")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(encrypt(PLAINTEXT, BASE_KEY) + "\n")
    print("wrote", os.path.normpath(out_path))


if __name__ == "__main__":
    main()
