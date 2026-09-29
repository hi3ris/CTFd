#!/usr/bin/env python3
"""
Static solver for 'keystore-alias'.

We parse the custom keystore blob (assets/vault.keystore), read the hardcoded
PASSPHRASE from KeyDeriver.java, and reproduce the per-alias key derivation and
keystream XOR for the "grant" alias. Nothing is hardcoded, so a rebuild solves.

Usage: python3 solve.py [path-to-entvault.apk]
"""

import hashlib
import re
import struct
import sys
import zipfile


def keystream(master: bytes, n: int) -> bytes:
    out = bytearray()
    j = 0
    while len(out) < n:
        out += hashlib.sha256(master + bytes([j])).digest()
        j += 1
    return bytes(out[:n])


def parse_entries(blob: bytes):
    assert blob[:4] == b"AKS1"
    count = blob[4]
    off = 5
    entries = []
    for _ in range(count):
        al = blob[off]
        off += 1
        alias = blob[off : off + al].decode()
        off += al
        salt = blob[off : off + 16]
        off += 16
        (enclen,) = struct.unpack(">H", blob[off : off + 2])
        off += 2
        enc = blob[off : off + enclen]
        off += enclen
        entries.append((alias, salt, enc))
    return entries


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "../entvault.apk"
    with zipfile.ZipFile(path) as z:
        blob = z.read("assets/vault.keystore")
        java = z.read("sources/com/enterprise/vault/KeyDeriver.java").decode()

    passphrase = re.search(r'PASSPHRASE\s*=\s*"([^"]+)"', java).group(1)
    # the code comment names the alias the app unlocks
    want = re.search(r'unlocks the "([^"]+)" alias', java).group(1)

    for alias, salt, enc in parse_entries(blob):
        master = hashlib.sha256(alias.encode() + salt + passphrase.encode()).digest()
        plain = bytes(c ^ k for c, k in zip(enc, keystream(master, len(enc))))
        tag = "TARGET" if alias == want else "decoy"
        print(f"[{tag}] {alias}: {plain.decode(errors='replace')}")
        if alias == want:
            flag = plain.decode()

    print("flag:", flag)
    assert flag.startswith("NCTF{") and flag.endswith("}")


if __name__ == "__main__":
    main()
