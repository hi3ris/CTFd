#!/usr/bin/env python3
"""
Reference solver for `sram-retention`.

Parses an AE-32 SRAM retention image per the datasheet and reconstructs the
interleaved vault (the key). Works on the challenge image and on every sample.

Usage:
    python3 solve.py ../retention.dump
    python3 solve.py ../samples/sample_03.dump
"""

import struct
import sys

MAGIC = b"AE32"
VAULT_BASE = 4      # vault registers start after the 4-byte bank tag "BNK"+id


def decode(data):
    filesize = len(data)

    if data[0:4] != MAGIC:
        raise ValueError("bad magic")

    nbanks = data[4]
    vault_len = data[5]
    stride = data[6]
    hdr_cksum = data[7]

    # Checksum covers header bytes 0..6 ONLY (not the base table).
    if (sum(data[0:7]) & 0xFF) != hdr_cksum:
        raise ValueError("header checksum mismatch")

    # Bank base table: nbanks * u16 LE at 0x08, stored EOF-relative.
    phys = []
    for i in range(nbanks):
        stored = struct.unpack_from("<H", data, 0x08 + 2 * i)[0]
        base = filesize - stored          # <-- the twist: distance from EOF
        # sanity: each bank starts with tag b"BNK" + logical id
        assert data[base:base + 3] == b"BNK", f"bank {i} tag missing at {base:#x}"
        assert data[base + 3] == i, f"bank {i} id mismatch"
        phys.append(base)

    # De-interleave: key[k] lives in logical bank (k % nbanks),
    # slot j = k // nbanks, at intra-offset VAULT_BASE + j*stride.
    out = bytearray(vault_len)
    for k in range(vault_len):
        logical = k % nbanks
        j = k // nbanks
        intra = VAULT_BASE + j * stride
        out[k] = data[phys[logical] + intra]

    return bytes(out)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "../retention.dump"
    with open(path, "rb") as f:
        data = f.read()
    print(decode(data).decode(errors="replace"))


if __name__ == "__main__":
    main()
