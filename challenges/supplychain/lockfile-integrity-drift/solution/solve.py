#!/usr/bin/env python3
"""Recover the flag from the lockfile-integrity-drift bundle.

Recompute the SRI (sha512) integrity of each shipped tarball and compare it to
the value pinned in package-lock.json. Exactly one mismatches: that tarball was
swapped and carries the flag (base64) inside its index.js.
"""

import base64
import gzip
import hashlib
import io
import json
import os
import re
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def sri(body):
    return "sha512-" + base64.b64encode(hashlib.sha512(body).digest()).decode()


def main():
    with open(os.path.join(ROOT, "package-lock.json")) as fh:
        lock = json.load(fh)

    tampered = None
    for _, entry in lock["packages"].items():
        tgz = entry["resolved"].rsplit("/", 1)[-1]
        with open(os.path.join(ROOT, tgz), "rb") as fh:
            body = fh.read()
        if sri(body) != entry["integrity"]:
            tampered = (tgz, body)
            break

    tgz, body = tampered
    with tarfile.open(fileobj=io.BytesIO(gzip.decompress(body))) as tar:
        index = tar.extractfile("package/index.js").read().decode()

    b64 = re.search(r"_sig = '([^']+)'", index).group(1)
    flag = base64.b64decode(b64).decode()
    print(flag)


if __name__ == "__main__":
    main()
