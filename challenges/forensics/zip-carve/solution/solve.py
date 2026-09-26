#!/usr/bin/env python3
"""Reference solver for zip-carve.

The central directory hides ``secret.txt``, so ``zipfile`` / ``unzip`` only see
``notes.txt``. Carve every ``PK\\x03\\x04`` local file header directly out of the
byte stream to recover the orphaned member. The orphaned member is DEFLATE
compressed (method 8), so its payload must be inflated (raw deflate).

    python3 solve.py ../archive.zip
"""
import struct
import sys
import zlib

LFH = 0x04034B50


def carve(blob: bytes):
    members = {}
    off = 0
    while True:
        idx = blob.find(b"PK\x03\x04", off)
        if idx < 0:
            break
        (
            sig,
            _ver,
            _flags,
            method,
            _t,
            _d,
            _crc,
            comp,
            _uncomp,
            namelen,
            extralen,
        ) = struct.unpack("<IHHHHHIIIHH", blob[idx : idx + 30])
        if sig != LFH:
            off = idx + 4
            continue
        name = blob[idx + 30 : idx + 30 + namelen].decode("latin-1")
        data_start = idx + 30 + namelen + extralen
        payload = blob[data_start : data_start + comp]
        if method == 0:  # stored
            members[name] = payload
        elif method == 8:  # deflate -> inflate the raw stream
            members[name] = zlib.decompress(payload, -15)
        off = data_start + comp
    return members


def main(path: str) -> None:
    blob = open(path, "rb").read()
    members = carve(blob)
    secret = members["secret.txt"].decode("latin-1")
    flag = secret.split("-> ", 1)[1].strip()
    print(flag)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../archive.zip")
