#!/usr/bin/env python3
"""Deterministic generator for the 'sub-wildcard' challenge.

An AWS IAM role (`ci-deployer`) trusts GitHub Actions via OIDC. Its trust policy
was supposed to admit only the `kekeli-cloud/media-svc` repo on the main branch,
but the `token.actions.githubusercontent.com:sub` condition uses a `StringLike`
wildcard `repo:kekeli-cloud/*` that admits *any* repo in the org -- including an
attacker's fork. Assuming the role grants `secretsmanager:GetSecretValue` on a
release secret.

We ship the trust policy, the role's identity policy, *several* captured OIDC
tokens (`oidc-token.json`), and the secret value encrypted with a keystream
derived from the OIDC `sub` that unlocked the role. Only one of the captured
tokens actually satisfies the trust policy's `StringLike` condition on `sub`;
the rest are decoys whose subjects fail the `repo:kekeli-cloud/*` pattern (wrong
org, look-alike org, or a hyphen-extended org name). The player must evaluate
the trust policy to pick the admitted token before sealing/unsealing the secret.
"""

import base64
import fnmatch
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

FLAG = b"NCTF{oidc_sub_wildcard_assumed_the_role}"
ATTACKER_SUB = "repo:kekeli-cloud/media-svc-fork:ref:refs/heads/feature/x"
SUB_PATTERN = "repo:kekeli-cloud/*"


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

# Several captured tokens. Exactly one satisfies the trust policy's StringLike
# `sub` condition (`repo:kekeli-cloud/*`); the others are decoys that fail it:
#   - different org entirely (`acme-corp/...`)
#   - hyphen-extended org that only looks like a prefix (`kekeli-cloud-staging/`)
#   - collapsed org name (`kekelicloud/...`)
#   - org path split differently (`kekeli/cloud-...`)
# The admitted token's `sub` is exactly what seals the release secret.
OIDC_TOKENS = [
    {
        "_comment": "Captured token #1 (partner CI in a different org).",
        "iss": "https://token.actions.githubusercontent.com",
        "aud": "sts.amazonaws.com",
        "sub": "repo:acme-corp/media-svc:ref:refs/heads/main",
        "repository": "acme-corp/media-svc",
        "repository_owner": "acme-corp",
        "ref": "refs/heads/main",
        "workflow": "release",
        "actor": "octo-ci",
    },
    {
        "_comment": "Captured token #2 (look-alike org, hyphen-extended).",
        "iss": "https://token.actions.githubusercontent.com",
        "aud": "sts.amazonaws.com",
        "sub": "repo:kekeli-cloud-staging/media-svc:ref:refs/heads/main",
        "repository": "kekeli-cloud-staging/media-svc",
        "repository_owner": "kekeli-cloud-staging",
        "ref": "refs/heads/main",
        "workflow": "deploy",
        "actor": "staging-bot",
    },
    {
        "_comment": "Captured token #3 (attacker fork inside the trusted org).",
        "iss": "https://token.actions.githubusercontent.com",
        "aud": "sts.amazonaws.com",
        "sub": ATTACKER_SUB,
        "repository": "kekeli-cloud/media-svc-fork",
        "repository_owner": "kekeli-cloud",
        "ref": "refs/heads/feature/x",
        "workflow": "deploy",
        "actor": "mallory",
    },
    {
        "_comment": "Captured token #4 (collapsed org name).",
        "iss": "https://token.actions.githubusercontent.com",
        "aud": "sts.amazonaws.com",
        "sub": "repo:kekelicloud/media-svc:ref:refs/heads/main",
        "repository": "kekelicloud/media-svc",
        "repository_owner": "kekelicloud",
        "ref": "refs/heads/main",
        "workflow": "deploy",
        "actor": "ci-runner",
    },
    {
        "_comment": "Captured token #5 (org path split differently).",
        "iss": "https://token.actions.githubusercontent.com",
        "aud": "sts.amazonaws.com",
        "sub": "repo:kekeli/cloud-media-svc:ref:refs/heads/main",
        "repository": "kekeli/cloud-media-svc",
        "repository_owner": "kekeli",
        "ref": "refs/heads/main",
        "workflow": "deploy",
        "actor": "kekeli-ci",
    },
]


def admitted_sub() -> str:
    """The single captured `sub` that satisfies the trust wildcard."""
    aud_expected = TRUST["Statement"][0]["Condition"]["StringEquals"][
        "token.actions.githubusercontent.com:aud"
    ]
    matches = [
        t["sub"]
        for t in OIDC_TOKENS
        if t["aud"] == aud_expected and fnmatch.fnmatchcase(t["sub"], SUB_PATTERN)
    ]
    assert len(matches) == 1, f"expected exactly one admitted token, got {matches}"
    return matches[0]


def main() -> None:
    sub = admitted_sub()
    assert sub == ATTACKER_SUB, "sealing key must be the admitted sub"
    with open(os.path.join(ROOT, "trust-policy.json"), "w", encoding="utf-8") as fh:
        json.dump(TRUST, fh, indent=2)
        fh.write("\n")
    with open(os.path.join(ROOT, "role-permissions.json"), "w", encoding="utf-8") as fh:
        json.dump(ROLE_PERMS, fh, indent=2)
        fh.write("\n")
    with open(os.path.join(ROOT, "oidc-token.json"), "w", encoding="utf-8") as fh:
        json.dump({"CapturedTokens": OIDC_TOKENS}, fh, indent=2)
        fh.write("\n")

    ct = xor(FLAG, hashlib.sha256(sub.encode()).digest())
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
