#!/usr/bin/env python3
"""Reference solver for gzip-tar-nest.

Peel the layers: gzip -> tar -> zip -> gzip -> tar -> flag.txt.

    python3 solve.py ../parcel.tar.gz
"""
import gzip
import io
import sys
import tarfile
import zipfile


def main(path: str) -> None:
    parcel = open(path, "rb").read()

    outer_tar = gzip.decompress(parcel)
    with tarfile.open(fileobj=io.BytesIO(outer_tar)) as tar:
        level2 = tar.extractfile("level2.zip").read()

    with zipfile.ZipFile(io.BytesIO(level2)) as zf:
        level3 = zf.read("level3.tar.gz")

    level3_tar = gzip.decompress(level3)
    with tarfile.open(fileobj=io.BytesIO(level3_tar)) as tar:
        flag = tar.extractfile("flag.txt").read().decode().strip()

    print(flag)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../parcel.tar.gz")
