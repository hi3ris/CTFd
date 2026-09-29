#!/usr/bin/env python3
"""
Static solver for 'crc-forge'.

The checker stores table[i] = crc32( bytes([i & 0xFF, flag[i]]) ). Each entry
depends on a single flag byte, so every byte is recoverable by brute force: for
index i, try all 256 candidate bytes and keep the one whose CRC matches table[i].

The table is a raw little-endian uint32 array in the binary. We do not know its
offset, so we slide a window: at each candidate offset, decode consecutive
entries (using the local index as the position salt) and keep the run that
spells NCTF{...}. Nothing is hardcoded.

Usage: python3 solve.py [path-to-chall]
"""

import binascii
import struct
import sys

PRINTABLE = range(0x20, 0x7F)


def byte_for(i, crc):
    for b in PRINTABLE:
        if binascii.crc32(bytes([i & 0xFF, b])) & 0xFFFFFFFF == crc:
            return b
    return None


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "../chall"
    data = open(path, "rb").read()

    for off in range(0, len(data) - 4, 4):
        # anchor: first 5 entries must decode to "NCTF{"
        out = bytearray()
        ok = True
        for i in range(5):
            (crc,) = struct.unpack_from("<I", data, off + 4 * i)
            b = byte_for(i, crc)
            if b is None:
                ok = False
                break
            out.append(b)
        if not ok or bytes(out) != b"NCTF{":
            continue
        # extend until closing brace
        i = 5
        while off + 4 * i + 4 <= len(data) and i < 96:
            (crc,) = struct.unpack_from("<I", data, off + 4 * i)
            b = byte_for(i, crc)
            if b is None:
                break
            out.append(b)
            i += 1
            if b == ord("}"):
                print("flag:", out.decode())
                return
    print("no solution found", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
