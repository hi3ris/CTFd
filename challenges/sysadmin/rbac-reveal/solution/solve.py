#!/usr/bin/env python3
"""Reference solver for 'rbac-reveal'.

A Kubernetes Secret's ``data`` values are base64 — encoding, not encryption. The
RBAC bundle grants the app ServiceAccount read access to every secret in the
namespace, so the value is readable. Here the ``token`` was base64'd once by the
deploy script before ``kubectl`` base64'd it again, so we decode twice.

Pure standard library (no YAML library needed — the field is a simple line).
"""

import base64
import os
import re


def solve(root: str) -> str:
    with open(os.path.join(root, "secret.yaml"), encoding="utf-8") as fh:
        text = fh.read()

    m = re.search(r"^\s*token:\s*(\S+)\s*$", text, flags=re.MULTILINE)
    if not m:
        raise SystemExit("token field not found in secret.yaml")
    value = m.group(1)
    print("[+] Secret data.token =", value)

    once = base64.b64decode(value).decode()
    print("[+] after first base64 decode:", once)
    flag = base64.b64decode(once).decode()
    print("[+] FLAG =", flag)
    return flag


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    solve(os.path.normpath(os.path.join(here, "..")))
