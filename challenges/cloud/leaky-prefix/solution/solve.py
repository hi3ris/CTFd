#!/usr/bin/env python3
"""Reference solver for 'leaky-prefix'.

Parse the bucket policy, expand the resource ARN patterns of every Allow
statement that grants s3:GetObject to an anonymous principal, and find which
inventoried object keys are actually matched. The buggy statement uses the
prefix "assets/public*" (wildcard before the slash), so it also grants public
read on the internal "assets/public-backup/..." object. Read that object; the
flag is inside it.
"""

import fnmatch
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
FLAG_RE = re.compile(r"NCTF\{[ -~]*?\}")


def load(name: str):
    with open(os.path.join(ROOT, name), encoding="utf-8") as fh:
        return json.load(fh)


def anonymous(principal) -> bool:
    if principal == "*":
        return True
    if isinstance(principal, dict):
        return "*" in [principal.get("AWS")] or principal.get("AWS") == "*"
    return False


def solve() -> str:
    policy = load("bucket-policy.json")
    index = load("object-index.json")
    bucket = index["Name"]
    keys = [c["Key"] for c in index["Contents"]]

    # collect anonymous s3:GetObject resource globs (relative to bucket)
    prefix = f"arn:aws:s3:::{bucket}/"
    globs = []
    for stmt in policy["Statement"]:
        if stmt.get("Effect") != "Allow" or not anonymous(stmt.get("Principal")):
            continue
        actions = stmt.get("Action")
        actions = actions if isinstance(actions, list) else [actions]
        if not any(a in ("s3:GetObject", "s3:*") for a in actions):
            continue
        res = stmt.get("Resource")
        res = res if isinstance(res, list) else [res]
        for arn in res:
            if arn.startswith(prefix):
                globs.append(arn[len(prefix) :])

    reachable = [k for k in keys if any(fnmatch.fnmatch(k, g) for g in globs)]
    print("[*] anonymous s3:GetObject globs:", globs)
    print("[*] publicly reachable objects:")
    for k in reachable:
        print("      -", k)

    for k in reachable:
        with open(os.path.join(ROOT, "objects", k), encoding="utf-8") as fh:
            body = fh.read()
        m = FLAG_RE.search(body)
        if m:
            print("[+] FLAG =", m.group())
            return m.group()
    raise SystemExit("flag not found in reachable objects")


if __name__ == "__main__":
    solve()
