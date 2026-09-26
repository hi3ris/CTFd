#!/usr/bin/env python3
"""Recover the flag from the pip-postinstall-hook bundle.

The sdist's setup.py hides its install-time payload as a hex string XOR'd with
a single-byte key, both present in the file. Deobfuscate statically (never run
setup.py) to reveal the flag.
"""

import gzip
import io
import os
import re
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main():
    with open(os.path.join(ROOT, "acme-license-check-1.0.0.tar.gz"), "rb") as fh:
        raw = gzip.decompress(fh.read())
    with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
        member = next(m for m in tar.getmembers() if m.name.endswith("setup.py"))
        setup = tar.extractfile(member).read().decode()

    key = int(re.search(r"_K = (\d+)", setup).group(1))
    blob = re.search(r'_B = "([0-9a-f]+)"', setup).group(1)

    data = bytes.fromhex(blob)
    src = bytes(c ^ key for c in data).decode()

    flag = re.search(r"NCTF\{[^}]+\}", src).group(0)
    print(flag)


if __name__ == "__main__":
    main()
