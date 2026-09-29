#!/usr/bin/env python3
"""
Static solver for 'deeplink-guard'.

The Swift router unlocks only for one exact deeplink and uses that deeplink's
canonical string as the decryption key. We read the four validation constants
(scheme, host, path, code) out of DeepLinkRouter.swift, rebuild the canonical
URL, and reproduce the SHA-256 keystream XOR over the ciphertext in
Secrets.plist. A rebuild with new constants still solves.

Usage: python3 solve.py [path-to-VaultApp.ipa]
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
    path = sys.argv[1] if len(sys.argv) > 1 else "../VaultApp.ipa"
    base = "Payload/VaultApp.app/"
    with zipfile.ZipFile(path) as z:
        swift = z.read(base + "DeepLinkRouter.swift").decode()
        secrets = z.read(base + "Secrets.plist").decode()

    scheme = re.search(r'kScheme\s*=\s*"([^"]+)"', swift).group(1)
    host = re.search(r'kHost\s*=\s*"([^"]+)"', swift).group(1)
    path_c = re.search(r'kPath\s*=\s*"/([^"]+)"', swift).group(1)
    code = re.search(r'kCode\s*=\s*"([^"]+)"', swift).group(1)

    canonical = f"{scheme}://{host}/{path_c}?code={code}"
    ct = base64.b64decode(
        re.search(r"<key>grant_ciphertext</key>\s*<string>([^<]+)<", secrets).group(1)
    )
    ks = keystream(canonical.encode(), len(ct))
    flag = bytes(c ^ k for c, k in zip(ct, ks)).decode()
    print("winning deeplink:", canonical)
    print("flag:", flag)
    assert flag.startswith("NCTF{") and flag.endswith("}")


if __name__ == "__main__":
    main()
