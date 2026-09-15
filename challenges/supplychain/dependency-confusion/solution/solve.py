#!/usr/bin/env python3
"""Recover the flag from the dependency-confusion bundle.

npm resolves the *highest* version across configured registries. The public
registry advertises 9.9.9 (>> the internal 1.2.3), so that tarball wins. Its
package.json ships a postinstall hook that base64-decodes an exfil command
containing the flag.
"""

import base64
import gzip
import io
import json
import os
import re
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def parse_version(v):
    return tuple(int(x) for x in v.split("."))


def main():
    metas = []
    for name in ("registry-internal.json", "registry-public.json"):
        with open(os.path.join(ROOT, name)) as fh:
            metas.append(json.load(fh))

    # Pick the highest advertised version across both registries.
    best = None
    for meta in metas:
        for ver in meta["versions"]:
            key = parse_version(ver)
            if best is None or key > best[0]:
                best = (key, ver, meta)
    _, version, meta = best
    tarball = f"acme-telemetry-{version}.tgz"

    # Extract package.json from the winning tarball, read the postinstall hook.
    with open(os.path.join(ROOT, tarball), "rb") as fh:
        raw = gzip.decompress(fh.read())
    with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
        pkg = json.load(tar.extractfile("package/package.json"))

    hook = pkg["scripts"]["postinstall"]
    b64 = re.search(r"Buffer\.from\('([^']+)','base64'\)", hook).group(1)
    decoded = base64.b64decode(b64).decode()

    flag = re.search(r"NCTF\{[^}]+\}", decoded).group(0)
    print(flag)


if __name__ == "__main__":
    main()
