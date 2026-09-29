"""Recover the flag from the ZIP archive appended to the shipped BMP.

Python's zipfile locates the end-of-central-directory record by scanning from
the end of the file and transparently handles the BMP prefix, so the polyglot
opens as an archive directly.
"""

import os
import zipfile

ART = os.path.join(os.path.dirname(__file__), "..", "banner.bmp")


def solve(path: str) -> str:
    with zipfile.ZipFile(path) as zf:
        name = next(n for n in zf.namelist() if n.endswith("flag.txt"))
        return zf.read(name).decode().strip()


if __name__ == "__main__":
    print(solve(ART))
