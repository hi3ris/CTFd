#!/usr/bin/env python3
"""Reference solver for 'sub-wildcard'.

1. Read the trust policy's StringEquals(`aud`) and StringLike(`sub`) conditions.
2. Evaluate every captured token in `oidc-token.json` against those conditions.
   Exactly one satisfies the wildcard (an attacker fork in the same org matches
   `repo:kekeli-cloud/*`); the decoys fail it (wrong org, look-alike org, etc.),
   so only that token can assume `ci-deployer` via AssumeRoleWithWebIdentity.
3. Confirm the role's identity policy grants GetSecretValue on the release
   secret -- it is reachable.
4. The sealed secret is XOR-encrypted with SHA256(admitted sub); decrypt it.
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
    tokens = load("oidc-token.json")["CapturedTokens"]
    perms = load("role-permissions.json")
    secret = load("release-secret.json")

    stmt = trust["Statement"][0]
    cond = stmt["Condition"]
    aud_expected = cond["StringEquals"]["token.actions.githubusercontent.com:aud"]
    sub_pattern = cond["StringLike"][SUB_KEY]
    assert stmt["Action"] == "sts:AssumeRoleWithWebIdentity"
    print(f"[*] trust wildcard sub = {sub_pattern!r}")

    # Evaluate the trust policy against every captured token; keep the admitted.
    admitted = []
    for tok in tokens:
        ok = tok.get("aud") == aud_expected and fnmatch.fnmatchcase(
            tok["sub"], sub_pattern
        )
        mark = "ADMITTED" if ok else "rejected"
        print(f"[*]   {mark}: {tok['sub']!r}")
        if ok:
            admitted.append(tok["sub"])
    assert len(admitted) == 1, f"expected exactly one admitted token: {admitted}"
    sub = admitted[0]
    print(f"[*] sealing sub = {sub!r}  (org-wide fork admitted by the wildcard)")

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
