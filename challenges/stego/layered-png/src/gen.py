"""Generate an RGB PNG whose LSB plane hides a ZIP that hides the flag.

Layers:
  1. LSB steganography across the R/G/B bytes carries a byte stream:
     a 4-byte big-endian length followed by that many ZIP bytes.
  2. The ZIP contains `stage2.txt`, whose content is the base64 of the flag.
"""

import base64
import io
import os
import zipfile

from PIL import Image

FLAG = b"NCTF{peel_the_layers_png_zip_flag}"
W, H = 160, 120
OUT = os.path.join(os.path.dirname(__file__), "..", "layers.png")


def build_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("stage2.txt", base64.b64encode(FLAG))
    return buf.getvalue()


def bits_of(payload: bytes):
    for byte in payload:
        for i in range(7, -1, -1):
            yield (byte >> i) & 1


def main() -> None:
    zip_bytes = build_zip()
    payload = len(zip_bytes).to_bytes(4, "big") + zip_bytes

    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        for x in range(W):
            px[x, y] = ((x * 5) % 256, (y * 7) % 256, ((x ^ y) * 3) % 256)

    raw = bytearray(img.tobytes())
    for i, bit in enumerate(bits_of(payload)):
        raw[i] = (raw[i] & ~1) | bit

    Image.frombytes("RGB", (W, H), bytes(raw)).save(OUT, "PNG")
    print("wrote", os.path.abspath(OUT), "payload bytes", len(payload))


if __name__ == "__main__":
    main()
