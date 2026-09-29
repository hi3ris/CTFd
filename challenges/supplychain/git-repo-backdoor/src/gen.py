#!/usr/bin/env python3
"""Generate the git-repo-backdoor artifact bundle.

Builds a real (bare) git repository as loose objects and ships it as a tar. The
history has an initial benign commit and a second commit that sneaks a
`.githooks/post-checkout` hook. The hook pipes a base64 blob into a shell; that
blob decodes to the flag.
"""

import base64
import hashlib
import io
import os
import tarfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)

FLAG = "NCTF{g1t_hook_backdoor_in_post_checkout_2ab8}"

OBJECTS = {}  # oid -> raw (header+content) bytes


def store(obj_type, content):
    header = f"{obj_type} {len(content)}\0".encode()
    raw = header + content
    oid = hashlib.sha1(raw).hexdigest()
    OBJECTS[oid] = raw
    return oid


def blob(data):
    return store("blob", data)


def tree(entries):
    # entries: list of (mode, name, oid); git sorts by name bytes.
    body = b""
    for mode, name, oid in sorted(entries, key=lambda e: e[1]):
        body += f"{mode} {name}\0".encode() + bytes.fromhex(oid)
    return store("tree", body)


def commit(tree_oid, parent, message, ts):
    lines = [f"tree {tree_oid}"]
    if parent:
        lines.append(f"parent {parent}")
    who = f"ACME CI <ci@acme.corp> {ts} +0000"
    lines.append(f"author {who}")
    lines.append(f"committer {who}")
    body = ("\n".join(lines) + "\n\n" + message + "\n").encode()
    return store("commit", body)


def build():
    # --- commit 1: benign baseline ---------------------------------------
    readme = blob(b"# acme-service\n\nInternal deploy tooling.\n")
    workflow = blob(
        b"name: ci\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
        b"    steps:\n      - run: make build\n"
    )
    wf_dir = tree([("100644", "ci.yml", workflow)])
    github_dir = tree([("40000", "workflows", wf_dir)])
    root1 = tree(
        [
            ("100644", "README.md", readme),
            ("40000", ".github", github_dir),
        ]
    )
    c1 = commit(root1, None, "initial import", 1700000000)

    # --- commit 2: sneaks in a post-checkout hook ------------------------
    payload = f"export ACME_DEPLOY_KEY={FLAG}\n"
    payload_b64 = base64.b64encode(payload.encode()).decode()
    hook = (
        "#!/bin/sh\n"
        "# provision deploy credentials on checkout\n"
        f"echo {payload_b64} | base64 -d | sh\n"
    ).encode()
    hook_blob = blob(hook)
    hooks_dir = tree([("100755", "post-checkout", hook_blob)])
    root2 = tree(
        [
            ("100644", "README.md", readme),
            ("40000", ".github", github_dir),
            ("40000", ".githooks", hooks_dir),
        ]
    )
    c2 = commit(root2, c1, "chore: add local dev hooks", 1700100000)

    # --- lay out a bare repo and tar it ----------------------------------
    def add(tar, name, data, mode=0o644):
        info = tarfile.TarInfo("acme-service.git/" + name)
        info.size = len(data)
        info.mode = mode
        info.mtime = 0
        tar.addfile(info, io.BytesIO(data))

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for oid, raw in OBJECTS.items():
            add(tar, f"objects/{oid[:2]}/{oid[2:]}", zlib.compress(raw))
        add(tar, "HEAD", b"ref: refs/heads/main\n")
        add(tar, "refs/heads/main", (c2 + "\n").encode())
        add(tar, "config", b"[core]\n\trepositoryformatversion = 0\n\tbare = true\n")

    with open(os.path.join(OUT, "acme-service.git.tar"), "wb") as fh:
        fh.write(buf.getvalue())

    print("built git-repo-backdoor artifacts (HEAD =", c2, ")")


if __name__ == "__main__":
    build()
