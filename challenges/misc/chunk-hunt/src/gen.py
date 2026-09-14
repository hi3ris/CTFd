#!/usr/bin/env python3
"""Build badge.png for chunk-hunt.

A normal-looking PNG is produced, then several ancillary ``tEXt`` chunks are
spliced in before ``IEND``. Each real chunk's keyword is ``frgNN`` and its text
is one slice of the base85-encoded flag; the slices are stored out of order.
One decoy ``Comment`` chunk holds a red herring. Concatenating the ``frg``
slices by index and base85-decoding yields the flag.
"""

import base64
import os
import struct
import zlib

from PIL import Image

FLAG = b"NCTF{ancillary_png_chunks_carry_secrets}"


def text_chunk(keyword: str, text: str) -> bytes:
    body = keyword.encode("latin-1") + b"\x00" + text.encode("latin-1")
    crc = zlib.crc32(b"tEXt" + body) & 0xFFFFFFFF
    return struct.pack(">I", len(body)) + b"tEXt" + body + struct.pack(">I", crc)


def main() -> None:
    img = Image.new("RGB", (96, 96))
    px = img.load()
    for y in range(96):
        for x in range(96):
            px[x, y] = ((x * 3) % 256, (y * 3) % 256, ((x + y) * 2) % 256)

    root = os.path.join(os.path.dirname(__file__), "..")
    tmp = os.path.join(root, "badge.png")
    img.save(tmp)

    with open(tmp, "rb") as fh:
        data = fh.read()

    # Encode + slice the flag into ordered fragments, then shuffle the order.
    payload = base64.b85encode(FLAG).decode("ascii")
    size = 5
    slices = [payload[i : i + size] for i in range(0, len(payload), size)]
    chunks = [text_chunk(f"frg{i:02d}", s) for i, s in enumerate(slices)]

    order = list(range(len(chunks)))
    # deterministic non-trivial reordering
    order = order[1::2] + order[0::2]
    chunks = [chunks[i] for i in order]
    chunks.insert(0, text_chunk("Comment", "created with the office badge maker"))

    iend = data.rfind(b"IEND") - 4  # start of the IEND length field
    out = data[:iend] + b"".join(chunks) + data[iend:]
    with open(tmp, "wb") as fh:
        fh.write(out)
    print("wrote", os.path.relpath(tmp), "bytes:", len(out), "fragments:", len(slices))


if __name__ == "__main__":
    main()
