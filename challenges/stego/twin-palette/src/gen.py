"""Generate an indexed (palette) PNG where the flag lives in the index LSBs.

The palette is built in pairs: index 2k and index 2k+1 hold the *same* RGB
colour. The cover picture is drawn using even indices, so flipping a pixel's
index low bit changes nothing visible. That low bit carries the flag (MSB first
per byte), terminated by a NUL byte.
"""

import os

from PIL import Image

FLAG = b"NCTF{twin_palette_indices_encode}"
W, H = 96, 64
OUT = os.path.join(os.path.dirname(__file__), "..", "mosaic.png")

# 16 base colours -> palette slots 0..31 (each colour duplicated on 2k / 2k+1).
BASE = [
    (20, 20, 30),
    (200, 60, 60),
    (60, 200, 90),
    (70, 110, 220),
    (230, 200, 60),
    (200, 100, 220),
    (60, 210, 210),
    (240, 140, 70),
    (120, 120, 120),
    (150, 40, 40),
    (40, 150, 70),
    (40, 70, 150),
    (180, 160, 40),
    (150, 70, 170),
    (40, 160, 160),
    (190, 110, 55),
]


def build_palette() -> list[int]:
    pal = []
    for r, g, b in BASE:
        pal += [r, g, b, r, g, b]  # 2k and 2k+1 identical
    pal += [0, 0, 0] * (256 - len(pal) // 3)
    return pal


def flag_bits(data: bytes):
    for byte in data:
        for i in range(7, -1, -1):
            yield (byte >> i) & 1


def main() -> None:
    img = Image.new("P", (W, H))
    img.putpalette(build_palette())

    indices = bytearray()
    for y in range(H):
        for x in range(W):
            base = ((x // 6) + (y // 4)) % len(BASE)
            indices.append((base * 2))  # even -> low bit 0 by default

    for i, bit in enumerate(flag_bits(FLAG + b"\x00")):
        indices[i] = (indices[i] & ~1) | bit

    img.putdata(bytes(indices))
    img.save(OUT, "PNG")
    print("wrote", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
