#!/usr/bin/env python3
"""Recover the flag from the lockfile-integrity-drift bundle.

Recompute the SRI (sha512) integrity of each shipped tarball and compare it to
the value pinned in package-lock.json. Exactly one mismatches. That drift is
caused by a block of bytes appended *after* the gzip member; those trailing
bytes are the payload. They are the flag XORed with a keystream derived from
that dependency's *pinned* integrity, so we:

  1. find the dep whose real sha512 != pinned integrity,
  2. split off the bytes trailing the gzip stream (the mismatch delta),
  3. XOR them with keystream(pinned integrity of that dep) to get the flag.

Reading the gzip member normally (tar/zgrep) never touches the payload.
"""

import base64
import hashlib
import os
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def sri(body):
    return "sha512-" + base64.b64encode(hashlib.sha512(body).digest()).decode()


def keystream(seed: bytes, n: int) -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hashlib.sha512(seed + ctr.to_bytes(4, "big")).digest()
        ctr += 1
    return bytes(out[:n])


def gzip_trailer(body: bytes) -> bytes:
    """Bytes appended after the first gzip member."""
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    d.decompress(body)
    d.flush()
    return d.unused_data


def main():
    import json

    with open(os.path.join(ROOT, "package-lock.json")) as fh:
        lock = json.load(fh)

    tampered = None
    for _, entry in lock["packages"].items():
        tgz = entry["resolved"].rsplit("/", 1)[-1]
        with open(os.path.join(ROOT, tgz), "rb") as fh:
            body = fh.read()
        if sri(body) != entry["integrity"]:
            tampered = (tgz, body, entry["integrity"])
            break

    tgz, body, pinned = tampered
    trailer = gzip_trailer(body)
    ks = keystream(pinned.encode(), len(trailer))
    flag = bytes(a ^ b for a, b in zip(trailer, ks)).decode()
    print(flag)


if __name__ == "__main__":
    main()
