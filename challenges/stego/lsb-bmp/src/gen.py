"""Generate a 24-bit BMP whose blue-channel LSBs encode the flag.

The flag bits (MSB first per byte) are written into the least significant bit
of the blue byte of successive stored pixels, terminated by a NUL byte.
"""

import os
import struct

FLAG = b"NCTF{lsb_blue_channel_whispers}"
WIDTH = 96
HEIGHT = 64
OUT = os.path.join(os.path.dirname(__file__), "..", "postcard.bmp")


def build_pixels() -> bytearray:
    """A smooth diagonal gradient stored bottom-up, BGR, rows padded to 4."""
    row_bytes = WIDTH * 3
    pad = (-row_bytes) % 4
    pixels = bytearray()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            b = (x * 2) % 256
            g = (y * 3) % 256
            r = (x + y) % 256
            pixels += bytes((b, g, r))
        pixels += b"\x00" * pad
    return pixels


def flag_bits(data: bytes):
    for byte in data:
        for i in range(7, -1, -1):
            yield (byte >> i) & 1


def embed(pixels: bytearray) -> None:
    # One blue byte per pixel; blue byte is the first of each BGR triple, but
    # padding bytes must be skipped, so walk pixel by pixel.
    row_bytes = WIDTH * 3
    pad = (-row_bytes) % 4
    stride = row_bytes + pad
    bits = list(flag_bits(FLAG + b"\x00"))
    idx = 0
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if idx >= len(bits):
                return
            pos = y * stride + x * 3  # blue byte
            pixels[pos] = (pixels[pos] & 0xFE) | bits[idx]
            idx += 1


def main() -> None:
    pixels = build_pixels()
    embed(pixels)
    offset = 54
    filesize = offset + len(pixels)
    file_header = struct.pack("<2sIHHI", b"BM", filesize, 0, 0, offset)
    info_header = struct.pack(
        "<IiiHHIIiiII",
        40,
        WIDTH,
        HEIGHT,
        1,
        24,
        0,
        len(pixels),
        2835,
        2835,
        0,
        0,
    )
    with open(OUT, "wb") as fh:
        fh.write(file_header)
        fh.write(info_header)
        fh.write(pixels)
    print("wrote", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
