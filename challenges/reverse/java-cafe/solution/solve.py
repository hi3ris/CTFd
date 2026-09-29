#!/usr/bin/env python3
"""
Static solver for 'java-cafe'.

The .class stores the flag in its constant pool as two strings:

    B = base64( xor(flag, K) )
    K = the repeating XOR key

Both are UTF-8 entries in the constant pool, so they appear verbatim in the
file. We enumerate the printable strings, treat each base64-looking one as B and
each short one as K, and keep the combination that base64-decodes and un-xors to
NCTF{...}. Nothing is hardcoded, so a rebuild with a new key/flag still solves.

You could equally run `javap -c Vault.class` to read the bytecode, or just run
`java Vault <flag>` once you have it.

Usage: python3 solve.py [path-to-Vault.class]
"""

import base64
import re
import sys


def strings(data, minlen=3):
    return [
        m.group().decode() for m in re.finditer(rb"[\x20-\x7e]{%d,}" % minlen, data)
    ]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "../Vault.class"
    data = open(path, "rb").read()
    ss = strings(data)

    # The constant-pool length byte can prefix a string (e.g. '(' == 0x28 == 40),
    # so scan for base64 runs *inside* each string rather than matching the whole.
    blobs = []
    for s in ss:
        blobs.extend(re.findall(r"[A-Za-z0-9+/]{16,}={0,2}", s))
    keys = [s.encode() for s in ss if 1 <= len(s) <= 16]

    for blob in blobs:
        try:
            enc = base64.b64decode(blob, validate=True)
        except Exception:
            continue
        for key in keys:
            flag = bytes(enc[i] ^ key[i % len(key)] for i in range(len(enc)))
            if flag.startswith(b"NCTF{") and flag.endswith(b"}") and flag.isascii():
                print("key :", key.decode())
                print("flag:", flag.decode())
                return
    print("no solution found", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
