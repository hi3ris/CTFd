#!/usr/bin/env python3
"""
Static solver for 'root-gate'.

The tamper check is irrelevant to static analysis: the decryption key is the
hardcoded BuildConfig.RELEASE_CHANNEL. We read the constant and the base64
ciphertext from the APK and reproduce the SHA-256 keystream XOR. A rebuild with
a new channel/flag still solves.

Usage: python3 solve.py [path-to-securebank.apk]
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
    path = sys.argv[1] if len(sys.argv) > 1 else "../securebank.apk"
    with zipfile.ZipFile(path) as z:
        strings = z.read("res/values/strings.xml").decode()
        buildconfig = z.read("sources/com/securebank/app/BuildConfig.java").decode()

    ct = base64.b64decode(
        re.search(r'name="secure_payload">([^<]+)<', strings).group(1)
    )
    channel = re.search(r'RELEASE_CHANNEL\s*=\s*"([^"]+)"', buildconfig).group(1)

    ks = keystream(channel.encode(), len(ct))
    flag = bytes(c ^ k for c, k in zip(ct, ks)).decode()
    print("RELEASE_CHANNEL:", channel)
    print("flag:", flag)
    assert flag.startswith("NCTF{") and flag.endswith("}")


if __name__ == "__main__":
    main()
