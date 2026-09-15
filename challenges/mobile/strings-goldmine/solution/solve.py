#!/usr/bin/env python3
"""
Static solver for 'strings-goldmine'.

The APK ships an encrypted blob in res/values/strings.xml and the XOR key
(API_SECRET) hardcoded in BuildConfig.java. We pull both straight out of the
bundle and un-XOR. Nothing is hardcoded here, so a rebuild still solves.

Usage: python3 solve.py [path-to-app-release.apk]
"""

import base64
import re
import sys
import zipfile


def xor(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "../app-release.apk"
    with zipfile.ZipFile(path) as z:
        strings = z.read("res/values/strings.xml").decode()
        buildconfig = z.read("sources/com/vault/app/BuildConfig.java").decode()

    enc_b64 = re.search(r'name="enc_blob">([^<]+)<', strings).group(1)
    secret = re.search(r'API_SECRET\s*=\s*"([^"]+)"', buildconfig).group(1)

    flag = xor(base64.b64decode(enc_b64), secret.encode()).decode()
    print("API_SECRET:", secret)
    print("flag:", flag)
    assert flag.startswith("NCTF{") and flag.endswith("}")


if __name__ == "__main__":
    main()
