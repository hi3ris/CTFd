#!/usr/bin/env python3
"""Reference solver for 'trail-of-keys'.

Walk the CloudTrail records. Find the GetSecretValue call against the sensitive
`prod/customer-export` secret; the caller's temporary ASIA access key identifies
the exfil session. Confirm that same session then PutObject'd the notes file.
The exfiltrated object is XOR-sealed with SHA256(that ASIA key); decrypt it to
read the flag.
"""

import base64
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
TARGET = "prod/customer-export"


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
    records = load("cloudtrail.json")["Records"]

    akid = None
    for r in records:
        if r["eventName"] == "GetSecretValue":
            sid = r.get("requestParameters", {}).get("secretId", "")
            if TARGET in sid:
                akid = r["userIdentity"]["accessKeyId"]
                print(f"[*] GetSecretValue on target by access key {akid}")
    assert akid, "no GetSecretValue on the target secret"

    # confirm the same session exfiltrated via PutObject
    exfil = [
        r
        for r in records
        if r["eventName"] == "PutObject" and r["userIdentity"]["accessKeyId"] == akid
    ]
    assert exfil, "session did not PutObject"
    print(
        "[*] same key wrote",
        exfil[0]["requestParameters"]["bucketName"]
        + "/"
        + exfil[0]["requestParameters"]["key"],
    )

    obj = load("exfil-notes.json")
    ct = base64.b64decode(obj["ciphertext_b64"])
    ks = keystream(hashlib.sha256(akid.encode()).digest(), len(ct))
    flag = bytes(a ^ b for a, b in zip(ct, ks)).decode()
    print("[+] FLAG =", flag)
    return flag


if __name__ == "__main__":
    solve()
