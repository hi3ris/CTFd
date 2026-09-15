#!/usr/bin/env python3
"""Generate cipher.txt: Vigenere-encrypt the flag with key WARMUP."""


def vig_encrypt(pt, key):
    out = []
    ki = 0
    for c in pt:
        if "a" <= c <= "z":
            k = ord(key[ki % len(key)].lower()) - 97
            out.append(chr((ord(c) - 97 + k) % 26 + 97))
            ki += 1
        elif "A" <= c <= "Z":
            k = ord(key[ki % len(key)].lower()) - 97
            out.append(chr((ord(c) - 65 + k) % 26 + 65))
            ki += 1
        else:
            out.append(c)
    return "".join(out)


FLAG = "NCTF{vigenere_with_a_known_key}"
KEY = "WARMUP"
with open("../cipher.txt", "w") as f:
    f.write(vig_encrypt(FLAG, KEY) + "\n")
