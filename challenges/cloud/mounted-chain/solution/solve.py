#!/usr/bin/env python3
"""Reference solver for 'mounted-chain'.

Prove the ServiceAccount `media-worker` can read the Secret (a RoleBinding ties
it to a Role granting get/list on secrets), then decode the mounted `token`
value. Kubernetes base64-encodes stored Secret data, and the app base64-encoded
the value again, so `token` must be decoded twice to recover the flag.
"""

import base64
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
FLAG_RE = re.compile(rb"NCTF\{[ -~]*?\}")


def read(name: str) -> str:
    with open(os.path.join(ROOT, name), encoding="utf-8") as fh:
        return fh.read()


def rbac_allows_secret_read() -> bool:
    role = read("role.yaml")
    binding = read("rolebinding.yaml")
    role_ok = "secrets" in role and "get" in role and "secret-reader" in role
    bind_ok = (
        "media-worker" in binding
        and "secret-reader" in binding
        and "ServiceAccount" in binding
    )
    return role_ok and bind_ok


def solve() -> str:
    assert rbac_allows_secret_read(), "SA cannot read secrets per RBAC"
    print("[*] RBAC: RoleBinding grants SA media-worker get/list on secrets -> OK")

    secret = read("secret.yaml")
    m = re.search(r"token:\s*(\S+)", secret)
    stored = m.group(1)
    print("[*] Secret.data.token =", stored)

    once = base64.b64decode(stored)  # k8s layer
    twice = base64.b64decode(once)  # app layer
    flag = FLAG_RE.search(twice)
    if not flag:
        raise SystemExit("flag not recovered")
    print("[*] decode #1 ->", once.decode())
    print("[+] FLAG =", flag.group().decode())
    return flag.group().decode()


if __name__ == "__main__":
    solve()
