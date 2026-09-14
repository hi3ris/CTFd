#!/usr/bin/env python3
"""
Static solver for 'prefs-vault'.

The captured SharedPreferences file gives the per-install salt and the base64
RC4-encrypted token. TokenStore.java gives the hardcoded pepper and the key
derivation (SHA-256 of pepper||salt). We reproduce it offline.

Usage: python3 solve.py [path-to-quicknotes.apk]
"""

import base64
import hashlib
import re
import sys
import zipfile


def rc4(key: bytes, data: bytes) -> bytes:
    s = list(range(256))
    j = 0
    for i in range(256):
        j = (j + s[i] + key[i % len(key)]) & 0xFF
        s[i], s[j] = s[j], s[i]
    out = bytearray()
    i = j = 0
    for b in data:
        i = (i + 1) & 0xFF
        j = (j + s[i]) & 0xFF
        s[i], s[j] = s[j], s[i]
        out.append(b ^ s[(s[i] + s[j]) & 0xFF])
    return bytes(out)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "../quicknotes.apk"
    with zipfile.ZipFile(path) as z:
        prefs = z.read("shared_prefs/vault_prefs.xml").decode()
        store = z.read("sources/com/notes/vault/TokenStore.java").decode()

    salt = re.search(r'name="device_salt">([^<]+)<', prefs).group(1)
    enc = base64.b64decode(re.search(r'name="enc_token">([^<]+)<', prefs).group(1))
    pepper = re.search(r'PEPPER\s*=\s*"([^"]+)"', store).group(1)

    key = hashlib.sha256(pepper.encode() + salt.encode()).digest()
    flag = rc4(key, enc).decode()
    print("pepper:", pepper, "| salt:", salt)
    print("flag:", flag)
    assert flag.startswith("NCTF{") and flag.endswith("}")


if __name__ == "__main__":
    main()
