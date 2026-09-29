#!/usr/bin/env python3
"""Recover the flag from the provenance-forgery bundle.

The signing key is leaked in ci-signing.key and the scheme is
sig = sha256(KEY || 0x0a || subject.sha256). Verify each release's provenance:
recompute the digest of the shipped artifact and the expected signature. The
one release whose signature fails verification is forged; its artifact carries
the flag.
"""

import base64
import hashlib
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main():
    key = None
    with open(os.path.join(ROOT, "ci-signing.key"), "rb") as fh:
        for line in fh:
            if line.startswith(b"SIGNING_KEY="):
                key = line.split(b"=", 1)[1].strip()

    prov_dir = os.path.join(ROOT, "provenance")
    forged = None
    for fn in os.listdir(prov_dir):
        with open(os.path.join(prov_dir, fn)) as fh:
            stmt = json.load(fh)
        subject = stmt["subject"][0]
        artifact = subject["name"]
        recorded = subject["digest"]["sha256"]

        body = open(os.path.join(ROOT, artifact), "rb").read()
        actual = hashlib.sha256(body).hexdigest()

        expected_sig = hashlib.sha256(key + b"\n" + recorded.encode()).hexdigest()
        sig_ok = stmt["signature"]["sig"] == expected_sig
        digest_ok = actual == recorded

        if not (sig_ok and digest_ok):
            forged = (artifact, body)

    artifact, body = forged
    import gzip
    import io
    import tarfile

    with tarfile.open(fileobj=io.BytesIO(gzip.decompress(body))) as tar:
        js = tar.extractfile("dist/app.js").read().decode()

    b64 = re.search(r"_t = '([^']+)'", js).group(1)
    flag = base64.b64decode(b64).decode()
    print(flag)


if __name__ == "__main__":
    main()
