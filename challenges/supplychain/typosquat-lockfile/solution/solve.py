#!/usr/bin/env python3
"""Recover the flag from the typosquat-lockfile bundle.

All legitimate dependencies resolve from registry.npmjs.org. Exactly one entry
is served from a different host — that is the typosquatted package. Its tarball
hides the flag as ROT13(base64(flag)).
"""

import base64
import codecs
import gzip
import io
import json
import os
import re
import tarfile
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main():
    with open(os.path.join(ROOT, "package-lock.json")) as fh:
        lock = json.load(fh)

    hosts = {}
    for path, entry in lock["packages"].items():
        host = urlparse(entry["resolved"]).netloc
        hosts.setdefault(host, []).append((path, entry))

    # The odd host out (fewest entries) is the attacker's mirror.
    evil_host = min(hosts, key=lambda h: len(hosts[h]))
    path, entry = hosts[evil_host][0]

    tgz = entry["resolved"].rsplit("/", 1)[-1]
    with open(os.path.join(ROOT, tgz), "rb") as fh:
        raw = gzip.decompress(fh.read())
    with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
        index = tar.extractfile("package/index.js").read().decode()

    hidden = re.search(r"_p = '([^']+)'", index).group(1)
    b64 = codecs.decode(hidden, "rot_13")
    flag = base64.b64decode(b64).decode()
    print(flag)


if __name__ == "__main__":
    main()
