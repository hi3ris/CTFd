#!/usr/bin/env python3
"""Deterministic generator for the 'passrole-ladder' challenge.

A dump of an AWS account's IAM: users, roles, and the customer-managed policy
documents. The low-privileged user `mallory` can create and invoke Lambda
functions AND pass a specific execution role to Lambda. That execution role can
read a production secret. So mallory escalates: create a function with
`lambda-exec-role` as its role, invoke it, and read the secret with the role's
permissions.

We ship the IAM dump and the target secret, XOR-sealed with a keystream derived
from the escalation target role's ARN (the role that PassRole hands to Lambda).
"""

import base64
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

ACCT = "444455556666"
FLAG = b"NCTF{passrole_lambda_became_admin}"
TARGET_ROLE_ARN = f"arn:aws:iam::{ACCT}:role/lambda-exec-role"
SECRET_ARN = f"arn:aws:secretsmanager:eu-west-1:{ACCT}:secret:prod/root-db-Ab12Cd"


def keystream(key: bytes, n: int) -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hashlib.sha256(key + ctr.to_bytes(4, "big")).digest()
        ctr += 1
    return bytes(out[:n])


USERS = {
    "Users": [
        {
            "UserName": "mallory",
            "Arn": f"arn:aws:iam::{ACCT}:user/mallory",
            "AttachedManagedPolicies": [
                {
                    "PolicyName": "ci-lambda-deployer",
                    "PolicyArn": f"arn:aws:iam::{ACCT}:policy/ci-lambda-deployer",
                }
            ],
        },
        {
            "UserName": "reporting-bot",
            "Arn": f"arn:aws:iam::{ACCT}:user/reporting-bot",
            "AttachedManagedPolicies": [
                {
                    "PolicyName": "read-metrics-only",
                    "PolicyArn": f"arn:aws:iam::{ACCT}:policy/read-metrics-only",
                }
            ],
        },
    ]
}

LAMBDA_TRUST = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }
    ],
}

ROLES = {
    "Roles": [
        {
            "RoleName": "lambda-exec-role",
            "Arn": TARGET_ROLE_ARN,
            "AssumeRolePolicyDocument": LAMBDA_TRUST,
            "AttachedManagedPolicies": [
                {
                    "PolicyName": "read-prod-secret",
                    "PolicyArn": f"arn:aws:iam::{ACCT}:policy/read-prod-secret",
                }
            ],
        },
        {
            # decoy: can read the secret, but its trust does NOT allow Lambda and
            # mallory cannot PassRole it -> not reachable from mallory.
            "RoleName": "break-glass-admin",
            "Arn": f"arn:aws:iam::{ACCT}:role/break-glass-admin",
            "AssumeRolePolicyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": f"arn:aws:iam::{ACCT}:root"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            },
            "AttachedManagedPolicies": [
                {
                    "PolicyName": "read-prod-secret",
                    "PolicyArn": f"arn:aws:iam::{ACCT}:policy/read-prod-secret",
                }
            ],
        },
        {
            # decoy: mallory CAN pass it and it trusts Lambda, but it cannot read
            # the secret -> dead end.
            "RoleName": "lambda-logs-role",
            "Arn": f"arn:aws:iam::{ACCT}:role/lambda-logs-role",
            "AssumeRolePolicyDocument": LAMBDA_TRUST,
            "AttachedManagedPolicies": [
                {
                    "PolicyName": "write-logs-only",
                    "PolicyArn": f"arn:aws:iam::{ACCT}:policy/write-logs-only",
                }
            ],
        },
    ]
}

POLICIES = {
    "Policies": {
        "ci-lambda-deployer": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "DeployLambdas",
                    "Effect": "Allow",
                    "Action": [
                        "lambda:CreateFunction",
                        "lambda:UpdateFunctionCode",
                        "lambda:InvokeFunction",
                    ],
                    "Resource": "*",
                },
                {
                    "Sid": "PassExecAndLogsRoles",
                    "Effect": "Allow",
                    "Action": "iam:PassRole",
                    "Resource": [
                        TARGET_ROLE_ARN,
                        f"arn:aws:iam::{ACCT}:role/lambda-logs-role",
                    ],
                    "Condition": {
                        "StringEquals": {"iam:PassedToService": "lambda.amazonaws.com"}
                    },
                },
            ],
        },
        "read-metrics-only": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["cloudwatch:GetMetricData"],
                    "Resource": "*",
                }
            ],
        },
        "read-prod-secret": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["secretsmanager:GetSecretValue"],
                    "Resource": SECRET_ARN,
                }
            ],
        },
        "write-logs-only": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
                    "Resource": "*",
                }
            ],
        },
    }
}


def main() -> None:
    for name, doc in (
        ("iam-users.json", USERS),
        ("iam-roles.json", ROLES),
        ("iam-policies.json", POLICIES),
    ):
        with open(os.path.join(ROOT, name), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2)
            fh.write("\n")

    ks = keystream(hashlib.sha256(TARGET_ROLE_ARN.encode()).digest(), len(FLAG))
    ct = bytes(a ^ b for a, b in zip(FLAG, ks))
    secret = {
        "SecretArn": SECRET_ARN,
        "_comment": "SecretString sealed for handout.",
        "seal": "XOR keystream = SHA256(ARN of the role PassRole hands to Lambda)",
        "ciphertext_b64": base64.b64encode(ct).decode(),
    }
    with open(os.path.join(ROOT, "prod-secret.json"), "w", encoding="utf-8") as fh:
        json.dump(secret, fh, indent=2)
        fh.write("\n")
    print(
        "[+] wrote iam-users.json, iam-roles.json, iam-policies.json, prod-secret.json"
    )


if __name__ == "__main__":
    main()
