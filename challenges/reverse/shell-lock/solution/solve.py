#!/usr/bin/env python3
"""
Static solver for 'shell-lock'.

The obfuscated shell script stores two assignments:

    _k = hex string of (password_byte ^ 0x2A)
    _b = base64( xor(flag, password) )

The script de-xors _k with 0x2A to rebuild the password, gates on it, then
XOR-decrypts _b with the password. We do the same statically: parse both
assignments out of the script text, recover the password, base64-decode _b, and
XOR. Nothing is hardcoded.

Usage: python3 solve.py [path-to-lock.sh]
"""

import base64
import re
import sys


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "../lock.sh"
    text = open(path).read()

    k = re.search(r"_k=([0-9a-fA-F]+)", text).group(1)
    b = re.search(r"_b=([A-Za-z0-9+/=]+)", text).group(1)

    password = bytes(int(k[i : i + 2], 16) ^ 0x2A for i in range(0, len(k), 2))
    enc = base64.b64decode(b)
    flag = bytes(enc[i] ^ password[i % len(password)] for i in range(len(enc)))

    print("password:", password.decode())
    print("flag    :", flag.decode())


if __name__ == "__main__":
    main()
