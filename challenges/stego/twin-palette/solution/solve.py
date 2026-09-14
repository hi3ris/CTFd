"""Recover the flag from the palette-index LSBs of the shipped PNG.

Loads the image in palette mode, reads the raw index of each pixel, and takes
its low bit. Because palette entries 2k and 2k+1 are identical colours, the
low bit is invisible yet carries the flag.
"""

import os

from PIL import Image

ART = os.path.join(os.path.dirname(__file__), "..", "mosaic.png")


def solve(path: str) -> str:
    img = Image.open(path)
    assert img.mode == "P", "expected a palette image"
    bits = [idx & 1 for idx in img.tobytes()]
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
