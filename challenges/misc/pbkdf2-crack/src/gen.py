#!/usr/bin/env python3
"""Generate the password hash and wordlist for pbkdf2-crack.

We ship a single PBKDF2-HMAC-SHA256 entry in a Django-style
``pbkdf2_sha256$<iterations>$<salt>$<b64 hash>`` string plus a wordlist that
contains the correct passphrase. The flag is derived from the recovered
passphrase, so it never appears in plaintext in any shipped file.
"""

import base64
import hashlib
import os
import random

PASSWORD = "sunshine_dragon_42"
ITERATIONS = 1200


def encode(password: str, salt: bytes, iterations: int) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    b64 = base64.b64encode(dk).decode().strip()
    return f"pbkdf2_sha256${iterations}${salt.decode()}${b64}"


def main() -> None:
    root = os.path.join(os.path.dirname(__file__), "..")
    salt = b"n0tr4nd0m"
    line = encode(PASSWORD, salt, ITERATIONS)
    with open(os.path.join(root, "hash.txt"), "w", encoding="utf-8") as fh:
        fh.write(line + "\n")

    rng = random.Random(1337)
    adjectives = [
        "sunshine",
        "midnight",
        "crimson",
        "silver",
        "golden",
        "frozen",
        "hidden",
        "electric",
        "quiet",
        "rapid",
    ]
    nouns = [
        "dragon",
        "falcon",
        "tiger",
        "otter",
        "raven",
        "willow",
        "harbor",
        "cactus",
        "comet",
        "ember",
    ]
    words = set()
    for adj in adjectives:
        for noun in nouns:
            for num in range(0, 20):
                words.add(f"{adj}_{noun}_{num}")
    words.add(PASSWORD)  # make sure the answer is present
    words = list(words)
    rng.shuffle(words)
    with open(os.path.join(root, "wordlist.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(words) + "\n")

    print("wrote hash.txt and wordlist.txt entries:", len(words))


if __name__ == "__main__":
    main()
