#!/usr/bin/env python3
"""Reference solver for 'passrole-ladder'.

Walk the IAM graph from user `mallory`:

  * her policy allows lambda:CreateFunction + lambda:InvokeFunction, and
    iam:PassRole to a set of roles (scoped to lambda.amazonaws.com).
  * find a role that is BOTH passable by her AND trusts lambda.amazonaws.com AND
    can read the production secret.

Only `lambda-exec-role` satisfies all three. mallory creates a function with
that role and invokes it to read the secret. The secret is XOR-sealed with
SHA256(that role's ARN); decrypt for the flag.
"""

import base64
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))


def load(name: str):
    with open(os.path.join(ROOT, name), encoding="utf-8") as fh:
        return json.load(fh)


def as_list(x):
    return x if isinstance(x, list) else [x]


def keystream(key: bytes, n: int) -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hashlib.sha256(key + ctr.to_bytes(4, "big")).digest()
        ctr += 1
    return bytes(out[:n])


def policy_allows(doc, action_needle):
    for st in doc["Statement"]:
        if st.get("Effect") != "Allow":
            continue
        for a in as_list(st.get("Action", [])):
            if (
                a == action_needle
                or a == "*"
                or (a.endswith(":*") and action_needle.startswith(a[:-1]))
            ):
                return st
    return None


def solve() -> str:
    users = load("iam-users.json")["Users"]
    roles = load("iam-roles.json")["Roles"]
    pols = load("iam-policies.json")["Policies"]
    secret = load("prod-secret.json")
    secret_arn = secret["SecretArn"]

    mallory = next(u for u in users if u["UserName"] == "mallory")
    m_pols = [pols[p["PolicyName"]] for p in mallory["AttachedManagedPolicies"]]

    can_create = any(policy_allows(d, "lambda:CreateFunction") for d in m_pols)
    can_invoke = any(policy_allows(d, "lambda:InvokeFunction") for d in m_pols)
    assert can_create and can_invoke, "mallory can't create/invoke lambdas"

    passable = set()
    for d in m_pols:
        st = policy_allows(d, "iam:PassRole")
        if st:
            passable.update(as_list(st["Resource"]))
    print("[*] mallory can create+invoke lambdas; PassRole ->")
    for r in passable:
        print("      -", r)

    winner = None
    for role in roles:
        arn = role["Arn"]
        if arn not in passable:
            continue
        trust = role["AssumeRolePolicyDocument"]
        trusts_lambda = any(
            st.get("Principal", {}).get("Service") == "lambda.amazonaws.com"
            for st in trust["Statement"]
        )
        if not trusts_lambda:
            continue
        role_pols = [pols[p["PolicyName"]] for p in role["AttachedManagedPolicies"]]
        reads_secret = False
        for d in role_pols:
            st = policy_allows(d, "secretsmanager:GetSecretValue")
            if st and secret_arn in as_list(st["Resource"]):
                reads_secret = True
        if reads_secret:
            winner = role
            break

    assert winner, "no escalation path found"
    print(f"[*] escalation target role = {winner['RoleName']} ({winner['Arn']})")
    print(
        "[*] path: CreateFunction(role=%s) -> InvokeFunction -> GetSecretValue"
        % winner["RoleName"]
    )

    ct = base64.b64decode(secret["ciphertext_b64"])
    ks = keystream(hashlib.sha256(winner["Arn"].encode()).digest(), len(ct))
    flag = bytes(a ^ b for a, b in zip(ct, ks)).decode()
    print("[+] FLAG =", flag)
    return flag


if __name__ == "__main__":
    solve()
