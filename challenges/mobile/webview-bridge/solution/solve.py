#!/usr/bin/env python3
"""
Static solver for 'webview-bridge'.

app.js calls AndroidBridge.getSecret(token) with a fixed token literal;
JsBridge.getSecret decrypts an embedded blob keyed by that token. We pull the
token from the JS and the ciphertext from the Java, then reproduce the SHA-256
keystream XOR. A rebuild with a new token/flag still solves.

Usage: python3 solve.py [path-to-hybridshop.apk]
"""

import base64
import hashlib
import re
import sys
import zipfile


def keystream(key: bytes, n: int) -> bytes:
    out = bytearray()
    j = 0
    while len(out) < n:
        out += hashlib.sha256(key + bytes([j])).digest()
        j += 1
    return bytes(out[:n])


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "../hybridshop.apk"
    with zipfile.ZipFile(path) as z:
        js = z.read("assets/app.js").decode()
        bridge = z.read("sources/com/hybrid/shop/JsBridge.java").decode()

    token = re.search(r'getSecret\(\s*"([^"]+)"', js)
    if not token:
        token = re.search(r'token\s*=\s*"([^"]+)"', js)
    token = token.group(1)
    enc = base64.b64decode(re.search(r'ENC\s*=\s*"([^"]+)"', bridge).group(1))

    ks = keystream(token.encode(), len(enc))
    flag = bytes(c ^ k for c, k in zip(enc, ks)).decode()
    print("bridge token:", token)
    print("flag:", flag)
    assert flag.startswith("NCTF{") and flag.endswith("}")


if __name__ == "__main__":
    main()
