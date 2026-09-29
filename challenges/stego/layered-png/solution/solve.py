"""Peel the layers of the shipped PNG to recover the flag.

  1. Read the LSB of every R/G/B byte to rebuild a byte stream.
  2. First 4 bytes are a big-endian length; the next N bytes are a ZIP.
  3. The ZIP holds `stage2.txt`, whose base64 content decodes to the flag.
"""

import base64
import io
import os
import zipfile

from PIL import Image

ART = os.path.join(os.path.dirname(__file__), "..", "layers.png")


def bits_to_bytes(bits) -> bytes:
    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        byte = 0
        for b in bits[i : i + 8]:
            byte = (byte << 1) | b
        out.append(byte)
    return bytes(out)


def solve(path: str) -> str:
    raw = Image.open(path).convert("RGB").tobytes()
    bits = [byte & 1 for byte in raw]
    stream = bits_to_bytes(bits)

    length = int.from_bytes(stream[:4], "big")
    zip_bytes = stream[4 : 4 + length]

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        stage2 = zf.read("stage2.txt")
    return base64.b64decode(stage2).decode()


if __name__ == "__main__":
    print(solve(ART))
