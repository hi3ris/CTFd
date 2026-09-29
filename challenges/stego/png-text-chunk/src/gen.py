"""Generate a PNG carrying the flag as base64 inside a tEXt metadata chunk.

A plausible plaintext comment is added as a decoy; the real payload sits in a
separate keyword whose value is base64-encoded.
"""

import base64
import os

from PIL import Image
from PIL.PngImagePlugin import PngInfo

FLAG = "NCTF{text_chunk_carries_secrets}"
OUT = os.path.join(os.path.dirname(__file__), "..", "sunset.png")


def main() -> None:
    img = Image.new("RGB", (120, 80))
    px = img.load()
    for y in range(80):
        for x in range(120):
            px[x, y] = (255 - y * 2, 120 + x, 40 + y)

    meta = PngInfo()
    meta.add_text("Description", "a lovely generated sunset, nothing to see")
    meta.add_text("Signature", base64.b64encode(FLAG.encode()).decode())

    img.save(OUT, "PNG", pnginfo=meta)
    print("wrote", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
