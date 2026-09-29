#!/usr/bin/env python3
"""
Static solver for 'native-xor'.

We parse the SBOX and KEY out of the decompiled native pseudocode, invert the
substitution box, and undo the per-index transform over assets/enc.bin:

    t = SBOX_INV[enc[i]]
    t ^= KEY[i % len(KEY)]
    flag[i] = (t - i) & 0xFF

Everything comes from the shipped bundle, so a rebuild still solves.

Usage: python3 solve.py [path-to-nativegame.apk]
"""

import re
import sys
import zipfile


def parse_bytes(block: str):
    return [int(x, 16) for x in re.findall(r"0x[0-9a-fA-F]{2}", block)]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "../nativegame.apk"
    with zipfile.ZipFile(path) as z:
        c_src = z.read("lib/arm64-v8a/decompiled_native.c").decode()
        enc = z.read("assets/enc.bin")

    sbox_block = re.search(r"SBOX\[256\]\s*=\s*\{(.*?)\}", c_src, re.S).group(1)
    sbox = parse_bytes(sbox_block)
    assert len(sbox) == 256
    key_block = re.search(r"KEY\[\d+\]\s*=\s*\{([^}]*)\}", c_src).group(1)
    key = parse_bytes(key_block)

    inv = [0] * 256
    for i, v in enumerate(sbox):
        inv[v] = i

    out = []
    for i, e in enumerate(enc):
        t = inv[e]
        t ^= key[i % len(key)]
        out.append((t - i) & 0xFF)
    flag = bytes(out).decode()
    print("key:", " ".join("%02x" % k for k in key))
    print("flag:", flag)
    assert flag.startswith("NCTF{") and flag.endswith("}")


if __name__ == "__main__":
    main()
