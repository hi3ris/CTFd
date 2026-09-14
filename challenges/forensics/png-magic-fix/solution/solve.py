#!/usr/bin/env python3
"""Reference solver for png-magic-fix.

Restore the standard PNG signature, then read the ``tEXt`` chunk metadata.

    python3 solve.py ../evidence.png
"""
import struct
import sys

PNG_SIG = b"\x89PNG\r\n\x1a\n"


def parse_text_chunks(png: bytes):
    off = 8
    out = {}
    while off + 8 <= len(png):
        (length,) = struct.unpack(">I", png[off : off + 4])
        tag = png[off + 4 : off + 8]
        data = png[off + 8 : off + 8 + length]
        if tag == b"tEXt":
            keyword, _, value = data.partition(b"\x00")
            out[keyword.decode("latin-1")] = value.decode("latin-1")
        off += 12 + length
        if tag == b"IEND":
            break
    return out


def main(path: str) -> None:
    raw = bytearray(open(path, "rb").read())
    # The first 8 bytes are wrong; repair the signature so the file is a PNG.
    raw[:8] = PNG_SIG
    texts = parse_text_chunks(bytes(raw))
    print(texts["Comment"])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../evidence.png")
