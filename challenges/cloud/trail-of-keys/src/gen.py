#!/usr/bin/env python3
"""Deterministic generator for the 'trail-of-keys' challenge.

A CloudTrail export covers a busy hour on the `kekeli-prod` account. Several
principals assume roles and get short-lived credentials (ASIA... access keys).
Exactly one of those sessions reads the sensitive secret and then writes an
exfiltration object to S3. We ship the trail plus the exfiltrated object, which
is XOR-sealed with a keystream derived from the ASIA access key of the session
that actually read the secret.
"""

import base64
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

FLAG = b"NCTF{cloudtrail_traced_the_asia_session}"
TARGET_SECRET = (
    "arn:aws:secretsmanager:us-east-1:333322221111:secret:prod/customer-export-Kd93js"
)
# the session that actually reads the secret + exfiltrates
EXFIL_AKID = "ASIA5EXFIL0SESSION07"


def keystream(key: bytes, n: int) -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hashlib.sha256(key + ctr.to_bytes(4, "big")).digest()
        ctr += 1
    return bytes(out[:n])


def ev(t, name, source, akid, arn, extra=None):
    e = {
        "eventTime": t,
        "eventName": name,
        "eventSource": source,
        "awsRegion": "us-east-1",
        "userIdentity": {"type": "AssumedRole", "accessKeyId": akid, "arn": arn},
    }
    if extra:
        e.update(extra)
    return e


def assume(t, akid, role, session, new_akid):
    return {
        "eventTime": t,
        "eventName": "AssumeRole",
        "eventSource": "sts.amazonaws.com",
        "awsRegion": "us-east-1",
        "userIdentity": {"type": "IAMUser", "accessKeyId": akid, "userName": session},
        "requestParameters": {"roleArn": role, "roleSessionName": session},
        "responseElements": {
            "credentials": {
                "accessKeyId": new_akid,
                "expiration": t.replace("T", " "),
            }
        },
    }


def build_trail():
    ar = "arn:aws:sts::333322221111:assumed-role"
    events = [
        assume(
            "2026-03-02T09:01:11Z",
            "AKIAOPS0BACKUPBOT01",
            "arn:aws:iam::333322221111:role/backup-writer",
            "nightly-backup",
            "ASIA5BACKUP0SESSION02",
        ),
        ev(
            "2026-03-02T09:02:40Z",
            "PutObject",
            "s3.amazonaws.com",
            "ASIA5BACKUP0SESSION02",
            f"{ar}/backup-writer/nightly-backup",
            {
                "requestParameters": {
                    "bucketName": "kekeli-backups",
                    "key": "db/2026-03-02.sql.gz",
                }
            },
        ),
        assume(
            "2026-03-02T09:05:03Z",
            "AKIADEV0ALICE000001",
            "arn:aws:iam::333322221111:role/read-metrics",
            "alice-cli",
            "ASIA5METRIC0SESSION3",
        ),
        ev(
            "2026-03-02T09:05:59Z",
            "GetMetricData",
            "monitoring.amazonaws.com",
            "ASIA5METRIC0SESSION3",
            f"{ar}/read-metrics/alice-cli",
        ),
        # attacker path: leaked user key assumes a role, then reads the secret
        assume(
            "2026-03-02T09:07:22Z",
            "AKIALEAK0MALLORY0001",
            "arn:aws:iam::333322221111:role/support-readonly",
            "session-9f2c",
            EXFIL_AKID,
        ),
        ev(
            "2026-03-02T09:07:58Z",
            "ListSecrets",
            "secretsmanager.amazonaws.com",
            EXFIL_AKID,
            f"{ar}/support-readonly/session-9f2c",
        ),
        ev(
            "2026-03-02T09:08:31Z",
            "GetSecretValue",
            "secretsmanager.amazonaws.com",
            EXFIL_AKID,
            f"{ar}/support-readonly/session-9f2c",
            {"requestParameters": {"secretId": TARGET_SECRET}},
        ),
        ev(
            "2026-03-02T09:09:12Z",
            "PutObject",
            "s3.amazonaws.com",
            EXFIL_AKID,
            f"{ar}/support-readonly/session-9f2c",
            {
                "requestParameters": {
                    "bucketName": "kekeli-scratch",
                    "key": "tmp/notes.bin",
                }
            },
        ),
        # decoy: a different session also reads a *different*, harmless secret
        assume(
            "2026-03-02T09:10:44Z",
            "AKIADEV0BOB00000002",
            "arn:aws:iam::333322221111:role/read-metrics",
            "bob-cli",
            "ASIA5DECOY0SESSION09",
        ),
        ev(
            "2026-03-02T09:11:20Z",
            "GetSecretValue",
            "secretsmanager.amazonaws.com",
            "ASIA5DECOY0SESSION09",
            f"{ar}/read-metrics/bob-cli",
            {
                "requestParameters": {
                    "secretId": "arn:aws:secretsmanager:us-east-1:333322221111:secret:dev/grafana-Zz01"
                }
            },
        ),
    ]
    return {"Records": events}


def main() -> None:
    with open(os.path.join(ROOT, "cloudtrail.json"), "w", encoding="utf-8") as fh:
        json.dump(build_trail(), fh, indent=2)
        fh.write("\n")

    ks = keystream(hashlib.sha256(EXFIL_AKID.encode()).digest(), len(FLAG))
    ct = bytes(a ^ b for a, b in zip(FLAG, ks))
    obj = {
        "_comment": "Exfiltrated object kekeli-scratch/tmp/notes.bin (sealed for handout).",
        "seal": "XOR keystream = SHA256(<ASIA access key of the session that read the target secret>)",
        "ciphertext_b64": base64.b64encode(ct).decode(),
    }
    with open(os.path.join(ROOT, "exfil-notes.json"), "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2)
        fh.write("\n")
    print("[+] wrote cloudtrail.json, exfil-notes.json")


if __name__ == "__main__":
    main()
