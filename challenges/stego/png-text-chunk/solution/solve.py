"""Recover the flag from the PNG's tEXt chunks.

Walks the PNG chunk stream manually (no image library needed), collects every
tEXt value, and base64-decodes each one looking for the flag.
"""

import base64
import os
import struct

ART = os.path.join(os.path.dirname(__file__), "..", "sunset.png")


def iter_text_values(data: bytes):
    pos = 8  # skip PNG signature
    while pos + 8 <= len(data):
        (length,) = struct.unpack_from(">I", data, pos)
        ctype = data[pos + 4 : pos + 8]
        body = data[pos + 8 : pos + 8 + length]
        if ctype == b"tEXt":
            _keyword, _sep, value = body.partition(b"\x00")
            yield value
        pos += 12 + length  # length + type + data + crc
        if ctype == b"IEND":
            break


def solve(path: str) -> str:
    with open(path, "rb") as fh:
        data = fh.read()
    for value in iter_text_values(data):
        try:
            decoded = base64.b64decode(value, validate=True).decode()
        except (ValueError, UnicodeDecodeError):
            continue
        if decoded.startswith("NCTF{"):
            return decoded
    raise SystemExit("flag not found")


if __name__ == "__main__":
    print(solve(ART))
