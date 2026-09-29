"""Generate a valid BMP with a ZIP archive appended after the pixel data.

Image viewers stop at the pixel data declared in the header and ignore the
trailing bytes; ZIP readers scan from the end of the file for the central
directory, so the same file is both a picture and an archive (a polyglot).
"""

import io
import os
import struct
import zipfile

FLAG = b"NCTF{zip_hides_past_the_pixels}\n"
WIDTH = 80
HEIGHT = 80
OUT = os.path.join(os.path.dirname(__file__), "..", "banner.bmp")


def build_bmp() -> bytes:
    row_bytes = WIDTH * 3
    pad = (-row_bytes) % 4
    pixels = bytearray()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            pixels += bytes(((x * 3) % 256, (y * 3) % 256, ((x + y) * 2) % 256))
        pixels += b"\x00" * pad
    offset = 54
    filesize = offset + len(pixels)
    header = struct.pack("<2sIHHI", b"BM", filesize, 0, 0, offset)
    info = struct.pack(
        "<IiiHHIIiiII", 40, WIDTH, HEIGHT, 1, 24, 0, len(pixels), 2835, 2835, 0, 0
    )
    return header + info + bytes(pixels)


def build_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("secret/flag.txt", FLAG)
    return buf.getvalue()


def main() -> None:
    with open(OUT, "wb") as fh:
        fh.write(build_bmp())
        fh.write(build_zip())
    print("wrote", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
