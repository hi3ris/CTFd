#!/usr/bin/env python3
"""Reference solver for 'gcp-token-scope'.

1. The leaked service-account key mints an OAuth token for `ci-helper`.
2. The project IAM policy grants that SA `roles/storage.objectViewer` at the
   PROJECT level, so the token can read every bucket -- including the private
   `kekeli-prod-artifacts` bucket that holds RELEASE_TOKEN.enc.
3. That object is XOR-sealed with SHA256(private_key_id) from the key; decrypt
   to read the flag.
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


def keystream(key: bytes, n: int) -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hashlib.sha256(key + ctr.to_bytes(4, "big")).digest()
        ctr += 1
    return bytes(out[:n])


def solve() -> str:
    sa = load("sa-key.json")
    policy = load("iam-policy.json")
    buckets = load("bucket-listing.json")

    member = f"serviceAccount:{sa['client_email']}"
    grants = [b["role"] for b in policy["bindings"] if member in b["members"]]
    print(f"[*] {member} project roles: {grants}")
    assert "roles/storage.objectViewer" in grants, "SA has no storage read"
    print("[*] project-wide objectViewer -> token can read ALL buckets")

    # locate the private artifact object the token can now reach
    target = None
    for b in buckets["buckets"]:
        for obj in b["objects"]:
            if obj.endswith("RELEASE_TOKEN.enc"):
                target = f"gs://{b['name']}/{obj}"
    print("[*] reachable private object:", target)

    sealed = load("release-token.json")
    ct = base64.b64decode(sealed["ciphertext_b64"])
    ks = keystream(hashlib.sha256(sa["private_key_id"].encode()).digest(), len(ct))
    flag = bytes(a ^ b for a, b in zip(ct, ks)).decode()
    print("[+] FLAG =", flag)
    return flag


if __name__ == "__main__":
    solve()
