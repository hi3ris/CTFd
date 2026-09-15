#!/usr/bin/env python3
"""Recover the flag from the tuf-rollback bundle.

The timestamp role says the current snapshot is version 8, but the served
snapshot.json is version 5 — a rollback. The stale snapshot pins targets
version 5, which points at a backdoored agent. Load that pinned target and read
the flag.
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


def load(name):
    with open(os.path.join(ROOT, name)) as fh:
        return json.load(fh)["signed"]


def main():
    timestamp = load("timestamp.json")
    snapshot = load("snapshot.json")

    expected = timestamp["meta"]["snapshot.json"]["version"]
    served = snapshot["version"]
    assert served < expected, "no rollback detected"

    # The stale snapshot pins this targets version.
    pinned = snapshot["meta"]["targets.json"]["version"]
    targets = load(f"targets-v{pinned}.json")
    assert targets["version"] == pinned

    name, meta = next(iter(targets["targets"].items()))
    body = open(os.path.join(ROOT, "targets", name), "rb").read()
    assert hashlib.sha256(body).hexdigest() == meta["hashes"]["sha256"]

    with tarfile.open(fileobj=io.BytesIO(gzip.decompress(body))) as tar:
        agent = tar.extractfile("agent.py").read().decode()

    b64 = re.search(r"_c = '([^']+)'", agent).group(1)
    flag = base64.b64decode(b64).decode()
    print(flag)


if __name__ == "__main__":
    main()
