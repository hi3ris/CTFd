#!/usr/bin/env python3
"""Deterministic generator for the 'leaky-prefix' challenge.

A production S3 bucket ("kekeli-media-prod") ships with a bucket policy that was
meant to make a small marketing folder world-readable. The prefix in the policy
is wrong: it matches an *internal* backup prefix instead, exposing one object
that should have stayed private.

We ship:
  * bucket-policy.json  -- the live S3 bucket policy
  * object-index.json   -- `aws s3api list-objects-v2` style inventory
  * objects/<key>       -- the object bodies (what `aws s3 sync` would pull)

The flag lives in the single object that the (broken) public statement actually
grants `s3:GetObject` on to `Principal: *`.
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

FLAG = "NCTF{public_read_on_the_wrong_prefix}"
BUCKET = "kekeli-media-prod"

# key -> (body, is-actually-public-per-policy)
OBJECTS = {
    "assets/public/logo.txt": "PNG logo asset, safe to serve on the CDN.\n",
    "assets/public/banner.txt": "Homepage banner copy, reviewed by marketing.\n",
    "assets/public/press-kit.txt": "Press kit blurb. Nothing sensitive here.\n",
    # This internal-backup prefix is the one the wildcard statement really hits.
    "assets/public-backup/db-snapshot-note.txt": (
        "INTERNAL RESTORE NOTE -- do not distribute.\n"
        "Snapshot vault passphrase handoff below.\n"
        f"{FLAG}\n"
    ),
    "internal/roadmap.txt": "Q3 roadmap draft. Confidential.\n",
    # exactly one decoy that looks flag-ish but is not reachable and not real
    "internal/old-ctf-note.txt": "legacy scratch: NCTF{not_the_flag_internal_only}\n",
}


def build_policy() -> dict:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "DenyInsecureTransport",
                "Effect": "Deny",
                "Principal": "*",
                "Action": "s3:*",
                "Resource": [
                    f"arn:aws:s3:::{BUCKET}",
                    f"arn:aws:s3:::{BUCKET}/*",
                ],
                "Condition": {"Bool": {"aws:SecureTransport": "false"}},
            },
            {
                # Intended: expose only assets/public/* to anonymous readers.
                # Typo: the trailing wildcard sits *before* the slash, so the
                # prefix becomes "assets/public" and also matches
                # "assets/public-backup/...".
                "Sid": "PublicMarketingRead",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{BUCKET}/assets/public*",
            },
        ],
    }


def build_index() -> dict:
    contents = []
    for key, body in OBJECTS.items():
        contents.append(
            {
                "Key": key,
                "Size": len(body.encode()),
                "StorageClass": "STANDARD",
            }
        )
    return {"Name": BUCKET, "KeyCount": len(contents), "Contents": contents}


def main() -> None:
    with open(os.path.join(ROOT, "bucket-policy.json"), "w", encoding="utf-8") as fh:
        json.dump(build_policy(), fh, indent=2)
        fh.write("\n")
    with open(os.path.join(ROOT, "object-index.json"), "w", encoding="utf-8") as fh:
        json.dump(build_index(), fh, indent=2)
        fh.write("\n")
    for key, body in OBJECTS.items():
        dest = os.path.join(ROOT, "objects", key)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(body)
    print("[+] wrote bucket-policy.json, object-index.json, objects/")


if __name__ == "__main__":
    main()
