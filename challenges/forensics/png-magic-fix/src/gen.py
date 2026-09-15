#!/usr/bin/env python3
"""Generate ``evidence.png`` for the png-magic-fix challenge.

The file is a perfectly valid PNG whose 8-byte signature has been overwritten
with zero bytes, so image viewers refuse to open it. The flag lives in a
``zTXt`` chunk (keyword ``Comment``) whose text is zlib-*compressed*, so a plain
``strings`` pass cannot read it. Restore the standard PNG signature, then locate
and inflate the compressed metadata to recover the note.
"""
import struct
import zlib

FLAG = "NCTF{png_m4gic_byt3s_r3st0r3d}"
PNG_SIG = b"\x89PNG\r\n\x1a\n"


def chunk(tag: bytes, data: bytes) -> bytes:
    body = tag + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))


def build_png() -> bytes:
    width, height = 16, 16
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB

    # A flat teal image; the picture itself is not the puzzle.
    raw = bytearray()
    for _ in range(height):
        raw.append(0)  # filter byte: none
        raw.extend(bytes((0x0E, 0x7A, 0x8C)) * width)
    idat = zlib.compress(bytes(raw), 9)

    # zTXt: keyword + NUL + compression method (0 = zlib) + zlib-compressed text.
    # The flag never appears in cleartext, so `strings` cannot surface it.
    ztxt = b"Comment\x00" + b"\x00" + zlib.compress(FLAG.encode(), 9)

    return (
        PNG_SIG
        + chunk(b"IHDR", ihdr)
        + chunk(b"zTXt", ztxt)
        + chunk(b"IDAT", idat)
        + chunk(b"IEND", b"")
    )


def main() -> None:
    png = build_png()
    # Corrupt the signature: overwrite the 8 magic bytes with zeros.
    corrupted = b"\x00" * 8 + png[8:]
    with open("evidence.png", "wb") as fh:
        fh.write(corrupted)
    print(f"wrote evidence.png ({len(corrupted)} bytes), flag={FLAG}")


if __name__ == "__main__":
    main()
