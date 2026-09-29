"""Recover the flag from the blue-channel LSBs of the shipped BMP.

Parses the BMP headers, walks the stored pixels bottom-up, and reads the least
significant bit of each blue byte until a NUL byte terminator is assembled.
"""

import os
import struct

ART = os.path.join(os.path.dirname(__file__), "..", "postcard.bmp")


def solve(path: str) -> str:
    with open(path, "rb") as fh:
        data = fh.read()
    (offset,) = struct.unpack_from("<I", data, 10)
    width, height = struct.unpack_from("<ii", data, 18)
    (bpp,) = struct.unpack_from("<H", data, 28)
    assert bpp == 24, "expected a 24-bit BMP"

    row_bytes = width * 3
    stride = row_bytes + ((-row_bytes) % 4)

    bits = []
    for y in range(height):
        for x in range(width):
            pos = offset + y * stride + x * 3
            bits.append(data[pos] & 1)

    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        byte = 0
        for b in bits[i : i + 8]:
            byte = (byte << 1) | b
        if byte == 0:
            break
        out.append(byte)
    return out.decode()


if __name__ == "__main__":
    print(solve(ART))
