#!/usr/bin/env python3
"""
Static solver for 'triple-wrap'.

The binary embeds the flag as three stacked layers:

    blob = base64( xor( rot13(flag), key ) )

To recover the flag we peel them in reverse:

    base64-decode(blob) -> xor with key -> un-rot13 (rot13 is its own inverse)

Both the base64 blob and the key are plain strings in the binary. We enumerate
printable strings, try each as the key against the base64-looking candidate, and
keep the combination that yields NCTF{...}. Nothing is hardcoded.

Usage: python3 solve.py [path-to-chall]
"""

import base64
import re
import sys


def strings(data, minlen=4):
    return [
        m.group().decode() for m in re.finditer(rb"[\x20-\x7e]{%d,}" % minlen, data)
    ]


def rot13(data):
    out = bytearray()
    for b in data:
        if 65 <= b <= 90:
            out.append((b - 65 + 13) % 26 + 65)
        elif 97 <= b <= 122:
            out.append((b - 97 + 13) % 26 + 97)
        else:
            out.append(b)
    return bytes(out)


def peel(blob, key):
    raw = base64.b64decode(blob)
    xored = bytes(raw[i] ^ key[i % len(key)] for i in range(len(raw)))
    return rot13(xored)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "../chall"
    data = open(path, "rb").read()
    ss = strings(data)

    b64re = re.compile(r"^[A-Za-z0-9+/]{16,}={0,2}$")
    blobs = [s for s in ss if b64re.match(s)]
    keys = [s.encode() for s in ss if 1 <= len(s) <= 16]

    for blob in blobs:
        for key in keys:
            try:
                cand = peel(blob, key)
            except Exception:
                continue
            if cand.startswith(b"NCTF{") and cand.endswith(b"}") and cand.isascii():
                print("key :", key.decode())
                print("flag:", cand.decode())
                return
    print("no solution found", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
