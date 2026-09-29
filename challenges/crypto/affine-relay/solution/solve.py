#!/usr/bin/env python3
"""Reference solver for 'affine-relay'.

An affine cipher over the 26-letter alphabet has only phi(26) * 26 = 12 * 26 =
312 possible keys. We brute-force every valid key, decrypt, and keep the one
decryption that contains the flag marker "NCTF{".
"""
import os
import sys
from math import gcd

MARKER = "NCTF{"


def decrypt(ct: str, a_inv: int, b: int) -> str:
    out = []
    for ch in ct:
        if "A" <= ch <= "Z":
            y = ord(ch) - ord("A")
            out.append(chr((a_inv * (y - b)) % 26 + ord("A")))
        else:
            out.append(ch)
    return "".join(out)


def solve(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        ct = fh.read()
    for a in range(1, 26):
        if gcd(a, 26) != 1:
            continue
        a_inv = pow(a, -1, 26)
        for b in range(26):
            pt = decrypt(ct, a_inv, b)
            if MARKER in pt:
                flag = pt[pt.index(MARKER) : pt.index("}", pt.index(MARKER)) + 1]
                print(f"[+] key found: a={a}, b={b}")
                print("[+] FLAG =", flag)
                return flag
    raise SystemExit("no key produced the flag marker")


if __name__ == "__main__":
    default = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "cipher.txt"
    )
    solve(sys.argv[1] if len(sys.argv) > 1 else default)
