#!/usr/bin/env python3
"""Recover the flag from the sbom-component-swap bundle.

Cross-reference every SBOM component's SHA-256 against the known-bad advisory
feed. The one match points to the compromised component; read its blob and
base64-decode the embedded config to get the flag.
"""

import base64
import hashlib
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main():
    with open(os.path.join(ROOT, "bom.json")) as fh:
        bom = json.load(fh)

    bad = set()
    with open(os.path.join(ROOT, "known-bad-hashes.txt")) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            bad.add(line.split()[0].lower())

    hit = None
    for comp in bom["components"]:
        for h in comp.get("hashes", []):
            if h["alg"] == "SHA-256" and h["content"].lower() in bad:
                hit = comp
    assert hit is not None

    blob = next(p["value"] for p in hit["properties"] if p["name"] == "blob")
    data = open(os.path.join(ROOT, blob), "rb").read()

    # Sanity: the blob really hashes to the flagged value.
    assert hashlib.sha256(data).hexdigest() in bad

    b64 = re.search(rb"cfg = '([^']+)'", data).group(1).decode()
    flag = base64.b64decode(b64).decode()
    print(flag)


if __name__ == "__main__":
    main()
