#!/usr/bin/env python3
"""Reference solver for 'vault-reuse'.

``bin/get-vault-pass.sh`` derives the vault password from committed, non-secret
metadata in ``group_vars/all.yml``:

    password = "<project>-<deploy_env>-vault-v1"

We read those two values, reproduce the password, and decrypt the
ansible-vault-styled ``group_vars/secrets.yml``.

Envelope: line 1 header, line 2 base64( salt(16) + iters(4 be) + ct );
``key = PBKDF2-HMAC-SHA256(password, salt, iters)`` and a
``SHA256(key || counter)`` keystream. Pure standard library.
"""

import base64
import hashlib
import os
import re


def keystream(key: bytes, n: int) -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hashlib.sha256(key + ctr.to_bytes(8, "big")).digest()
        ctr += 1
    return bytes(out[:n])


def read_metadata(path: str) -> dict:
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"^(\w+):\s*(\S+)\s*$", line)
            if m:
                out[m.group(1)] = m.group(2)
    return out


def solve(root: str) -> str:
    meta = read_metadata(os.path.join(root, "group_vars", "all.yml"))
    # Reproduce bin/get-vault-pass.sh: "<project>-<deploy_env>-vault-v1"
    password = f"{meta['project']}-{meta['deploy_env']}-vault-v1"
    print("[+] derived vault password:", password)

    with open(os.path.join(root, "group_vars", "secrets.yml"), encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    if not lines[0].startswith("$VAULT;"):
        raise SystemExit("not a recognised vault file")
    raw = base64.b64decode(lines[1])
    salt, iters, ct = raw[:16], int.from_bytes(raw[16:20], "big"), raw[20:]

    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iters)
    pt = bytes(a ^ b for a, b in zip(ct, keystream(key, len(ct)))).decode()
    print("[+] FLAG =", pt)
    return pt


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    solve(os.path.normpath(os.path.join(here, "..")))
