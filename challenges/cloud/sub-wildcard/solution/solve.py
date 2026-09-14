#!/usr/bin/env python3
"""Reference solver for 'sub-wildcard'.

1. Read the trust policy's StringLike condition on the OIDC `sub` claim.
2. Confirm the captured token's `sub` matches that wildcard (an attacker fork in
   the same org still matches `repo:kekeli-cloud/*`), so `ci-deployer` can be
   assumed via sts:AssumeRoleWithWebIdentity.
3. Confirm the role's identity policy grants GetSecretValue on the release
   secret -- it is reachable.
4. The sealed secret is XOR-encrypted with SHA256(sub); decrypt to get the flag.
"""

import base64
import fnmatch
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SUB_KEY = "token.actions.githubusercontent.com:sub"


def load(name: str):
    with open(os.path.join(ROOT, name), encoding="utf-8") as fh:
        return json.load(fh)


def keystream(key: bytes, n: int) -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hashlib.sha256(key + ctr.to_bytes(4, "big")).digest()
        ctr += 1
    return bytes(out[:n])


def solve() -> str:
    trust = load("trust-policy.json")
    token = load("oidc-token.json")
    perms = load("role-permissions.json")
    secret = load("release-secret.json")

    stmt = trust["Statement"][0]
    cond = stmt["Condition"]
    aud_expected = cond["StringEquals"]["token.actions.githubusercontent.com:aud"]
    sub_pattern = cond["StringLike"][SUB_KEY]
    sub = token["sub"]

    assert token["aud"] == aud_expected, "aud mismatch"
    assert fnmatch.fnmatch(sub, sub_pattern), "sub does not match trust wildcard"
    assert stmt["Action"] == "sts:AssumeRoleWithWebIdentity"
    print(f"[*] trust wildcard sub = {sub_pattern!r}")
    print(f"[*] presented    sub = {sub!r}  -> MATCHES (org-wide fork admitted)")

    actions = perms["AttachedPolicy"]["Statement"][0]["Action"]
    assert "secretsmanager:GetSecretValue" in actions
    print("[*] ci-deployer grants secretsmanager:GetSecretValue -> secret reachable")

    ct = base64.b64decode(secret["SecretStringCiphertextB64"])
    pt = bytes(
        a ^ b
        for a, b in zip(ct, keystream(hashlib.sha256(sub.encode()).digest(), len(ct)))
    )
    flag = pt.decode()
    print("[+] FLAG =", flag)
    return flag


if __name__ == "__main__":
    solve()
