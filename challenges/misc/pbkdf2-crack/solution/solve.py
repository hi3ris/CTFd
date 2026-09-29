#!/usr/bin/env python3
"""Crack the shipped PBKDF2-HMAC-SHA256 hash with the shipped wordlist."""

import base64
import hashlib
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")


def main() -> None:
    with open(os.path.join(ROOT, "hash.txt"), encoding="utf-8") as fh:
        algo, iterations, salt, b64 = fh.read().strip().split("$")
    assert algo == "pbkdf2_sha256"
    iterations = int(iterations)
    target = base64.b64decode(b64)

    with open(os.path.join(ROOT, "wordlist.txt"), encoding="utf-8") as fh:
        for word in fh:
            word = word.strip()
            dk = hashlib.pbkdf2_hmac("sha256", word.encode(), salt.encode(), iterations)
            if dk == target:
                print("NCTF{pbkdf2_" + word + "}")
                return
    raise SystemExit("no match found")


if __name__ == "__main__":
    main()
