#!/usr/bin/env python3
"""Deterministic generator for the 'sub-wildcard' challenge.

An AWS IAM role (`ci-deployer`) trusts GitHub Actions via OIDC. Its trust policy
was supposed to admit only the `kekeli-cloud/media-svc` repo on the main branch,
but the `token.actions.githubusercontent.com:sub` condition uses a `StringLike`
wildcard `repo:kekeli-cloud/*` that admits *any* repo in the org -- including an
attacker's fork. Assuming the role grants `secretsmanager:GetSecretValue` on a
release secret.

We ship the trust policy, the role's identity policy, a captured OIDC token's
decoded claims (from the attacker's fork), and the secret value encrypted with a
keystream derived from the OIDC `sub` that unlocked the role.
"""

import base64
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

FLAG = b"NCTF{oidc_sub_wildcard_assumed_the_role}"
ATTACKER_SUB = "repo:kekeli-cloud/media-svc-fork:ref:refs/heads/feature/x"


def keystream(key: bytes, n: int) -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hashlib.sha256(key + ctr.to_bytes(4, "big")).digest()
        ctr += 1
    return bytes(out[:n])


def xor(data: bytes, key: bytes) -> bytes:
    ks = keystream(key, len(data))
    return bytes(a ^ b for a, b in zip(data, ks))


TRUST = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": (
                    "arn:aws:iam::210987654321:oidc-provider/"
                    "token.actions.githubusercontent.com"
                )
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                },
                "StringLike": {
                    # BUG: should pin one repo + branch, e.g.
                    # repo:kekeli-cloud/media-svc:ref:refs/heads/main
                    "token.actions.githubusercontent.com:sub": "repo:kekeli-cloud/*"
                },
            },
        }
    ],
}

ROLE_PERMS = {
    "RoleName": "ci-deployer",
    "AttachedPolicy": {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ReadReleaseSecret",
                "Effect": "Allow",
                "Action": ["secretsmanager:GetSecretValue"],
                "Resource": (
                    "arn:aws:secretsmanager:us-east-1:210987654321:"
                    "secret:prod/release-signing-*"
                ),
            }
        ],
    },
}

OIDC_TOKEN = {
    "_comment": "Decoded claims of the OIDC JWT presented by the attacker fork.",
    "iss": "https://token.actions.githubusercontent.com",
    "aud": "sts.amazonaws.com",
    "sub": ATTACKER_SUB,
    "repository": "kekeli-cloud/media-svc-fork",
    "repository_owner": "kekeli-cloud",
    "ref": "refs/heads/feature/x",
    "workflow": "deploy",
    "actor": "mallory",
}


def main() -> None:
    with open(os.path.join(ROOT, "trust-policy.json"), "w", encoding="utf-8") as fh:
        json.dump(TRUST, fh, indent=2)
        fh.write("\n")
    with open(os.path.join(ROOT, "role-permissions.json"), "w", encoding="utf-8") as fh:
        json.dump(ROLE_PERMS, fh, indent=2)
        fh.write("\n")
    with open(os.path.join(ROOT, "oidc-token.json"), "w", encoding="utf-8") as fh:
        json.dump(OIDC_TOKEN, fh, indent=2)
        fh.write("\n")

    ct = xor(FLAG, hashlib.sha256(ATTACKER_SUB.encode()).digest())
    meta = {
        "Name": "prod/release-signing-key",
        "ARN": (
            "arn:aws:secretsmanager:us-east-1:210987654321:"
            "secret:prod/release-signing-key-a1b2c3"
        ),
        "Note": (
            "SecretString is sealed for this handout: XOR keystream = "
            "SHA256(<the OIDC sub that satisfied the trust policy>)."
        ),
        "SecretStringCiphertextB64": base64.b64encode(ct).decode(),
    }
    with open(os.path.join(ROOT, "release-secret.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
        fh.write("\n")
    print(
        "[+] wrote trust-policy.json, role-permissions.json, oidc-token.json, "
        "release-secret.json"
    )


if __name__ == "__main__":
    main()
