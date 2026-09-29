#!/usr/bin/env python3
"""Recover the flag from the git-repo-backdoor bundle.

Parse the loose git objects out of the shipped bare repo, walk the history to
the commit that adds `.githooks/post-checkout`, then decode the base64 blob the
hook pipes into a shell.
"""

import base64
import io
import os
import re
import tarfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main():
    with open(os.path.join(ROOT, "acme-service.git.tar"), "rb") as fh:
        tar = tarfile.open(fileobj=io.BytesIO(fh.read()))

    objects = {}
    head_ref = None
    refs = {}
    for m in tar.getmembers():
        if not m.isfile():
            continue
        data = tar.extractfile(m).read()
        rel = m.name.split("/", 1)[1]
        if rel.startswith("objects/"):
            parts = rel.split("/")
            oid = parts[1] + parts[2]
            objects[oid] = zlib.decompress(data)
        elif rel == "HEAD":
            head_ref = data.decode().strip().split()[-1]
        elif rel.startswith("refs/"):
            refs[rel] = data.decode().strip()

    def read(oid):
        raw = objects[oid]
        typ, rest = raw.split(b" ", 1)
        _, content = rest.split(b"\0", 1)
        return typ.decode(), content

    def parse_tree(content):
        entries = []
        i = 0
        while i < len(content):
            j = content.index(b"\0", i)
            mode, name = content[i:j].split(b" ", 1)
            oid = content[j + 1 : j + 21].hex()
            entries.append((mode.decode(), name.decode(), oid))
            i = j + 21
        return entries

    # Resolve HEAD to a commit and collect the whole history.
    tip = refs[head_ref]
    history = []
    cur = tip
    while cur:
        _, content = read(cur)
        history.append((cur, content))
        m = re.search(rb"^parent ([0-9a-f]{40})", content, re.M)
        cur = m.group(1).decode() if m else None

    # Find the commit whose tree contains .githooks/post-checkout.
    def find_hook(tree_oid, path=""):
        for mode, name, oid in parse_tree(read(tree_oid)[1]):
            full = f"{path}/{name}" if path else name
            if mode == "40000":
                r = find_hook(oid, full)
                if r:
                    return r
            elif full == ".githooks/post-checkout":
                return oid
        return None

    hook_oid = None
    for _, content in history:
        tree_oid = re.search(rb"^tree ([0-9a-f]{40})", content, re.M).group(1).decode()
        hook_oid = find_hook(tree_oid)
        if hook_oid:
            break

    hook = read(hook_oid)[1].decode()
    b64 = re.search(r"echo (\S+) \| base64 -d", hook).group(1)
    decoded = base64.b64decode(b64).decode()
    flag = re.search(r"NCTF\{[^}]+\}", decoded).group(0)
    print(flag)


if __name__ == "__main__":
    main()
