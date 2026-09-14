#!/usr/bin/env python3
"""Parse badge.png's tEXt chunks, reorder the flag fragments, base85-decode."""

import base64
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
PNG = os.path.join(HERE, "..", "badge.png")


def iter_chunks(data: bytes):
    off = 8  # skip PNG signature
    while off < len(data):
        (length,) = struct.unpack(">I", data[off : off + 4])
        ctype = data[off + 4 : off + 8].decode("latin-1")
        body = data[off + 8 : off + 8 + length]
        yield ctype, body
        off += 12 + length


def main() -> None:
    with open(PNG, "rb") as fh:
        data = fh.read()

    fragments = {}
    for ctype, body in iter_chunks(data):
        if ctype != "tEXt":
            continue
        keyword, _, text = body.partition(b"\x00")
        keyword = keyword.decode("latin-1")
        if keyword.startswith("frg"):
            fragments[int(keyword[3:])] = text.decode("latin-1")

    payload = "".join(fragments[i] for i in sorted(fragments))
    print(base64.b85decode(payload).decode())


if __name__ == "__main__":
    main()
