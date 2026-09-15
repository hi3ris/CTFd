#!/usr/bin/env python3
"""Recover the flag from the build-cache-poison bundle.

Parse the Makefile recipes: every vendor-cache fetch runs `sha256sum -c` except
one. That un-verified artifact is poisoned; its payload is
base64(XOR(flag, XOR_KEY)), with XOR_KEY declared in the Makefile.
"""

import base64
import gzip
import io
import os
import re
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main():
    text = open(os.path.join(ROOT, "Makefile")).read()

    xor_key = int(re.search(r"XOR_KEY := (\d+)", text).group(1))

    # Split into target recipe blocks (target line + tab-indented commands).
    blocks = re.findall(r"^(vendor-cache/\S+):\n((?:\t.*\n?)+)", text, re.M)
    poisoned = None
    for target, recipe in blocks:
        if "sha256sum" not in recipe:
            poisoned = target
            break

    artifact = os.path.join(ROOT, poisoned)
    with open(artifact, "rb") as fh:
        raw = gzip.decompress(fh.read())
    with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
        name = tar.getnames()[0]
        payload = tar.extractfile(name).read().decode()

    b64 = re.search(r"BUILD_TOKEN=(\S+)", payload).group(1)
    xored = base64.b64decode(b64)
    flag = bytes(b ^ xor_key for b in xored).decode()
    print(flag)


if __name__ == "__main__":
    main()
